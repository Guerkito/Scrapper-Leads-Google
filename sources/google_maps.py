import urllib.parse
from typing import List
from playwright.async_api import async_playwright
from loguru import logger
from sources.base_source import BaseSource, Lead
from db import clean_phone_number
from engine.maps_helpers import (
    BROWSER_ARGS, _RATING_SELECTORS, _REVIEW_SELECTORS,
    _WEB_SELECTORS, _TYPE_SELECTORS, _ADDRESS_SELECTORS, _PHONE_SELECTORS,
    _wait_for_panel, _is_captcha, _scroll_and_wait, _is_end_of_results,
    _extract_place_coordinates, _extract_place_id, _claim_place_for_scrape,
    _parse_rating, _parse_review_count, _extract_phone_candidate,
    click_cookie_consent,
)


async def _element_values(element) -> tuple[str, str, str]:
    """Retorna data-item-id, aria-label y texto sin fallar por un nodo incompleto."""
    if not element:
        return "", "", ""
    values = []
    for attribute in ("data-item-id", "aria-label"):
        try:
            values.append(await element.get_attribute(attribute) or "")
        except Exception:
            values.append("")
    try:
        values.append(await element.inner_text() or "")
    except Exception:
        values.append("")
    return tuple(values)


async def _panel_element(_page, panel, selector):
    """Evita tomar rating o contacto de una tarjeta del listado lateral."""
    if not panel:
        return None
    return await panel.query_selector(selector)

class GoogleMapsSource(BaseSource):
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        """
        Implementación completa del scraper de Google Maps.
        """
        if ciudad.startswith("coord:"):
            _, coords_str = ciudad.split(":", 1)
            try:
                clat, clng, czoom = coords_str.split(",")
                float(clat), float(clng)
            except (ValueError, AttributeError):
                logger.warning(f"GoogleMaps: coordenadas malformadas en '{ciudad[:60]}'")
                return []
            url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}/@{clat},{clng},{czoom}z?hl=es"
        else:
            search_query = f"{query} en {ciudad}"
            url = f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}/?hl=es"

        # Extraer parámetros de control
        browser_context = kwargs.pop("context", None)
        max_results = kwargs.pop("limit", 20)
        l_callback = kwargs.pop("lead_callback", None)
        stop_check = kwargs.pop("stop_check", lambda: False)
        hunter_mode = kwargs.pop("hunter_mode", False)
        known_place_ids = kwargs.pop("known_place_ids", None)
        seen_place_ids = kwargs.pop("seen_place_ids", None)

        if browser_context:
            return await self._execute_scrape(
                browser_context, url, query, ciudad, limit=max_results,
                lead_callback=l_callback, stop_check=stop_check,
                hunter_mode=hunter_mode, known_place_ids=known_place_ids,
                seen_place_ids=seen_place_ids,
            )
        else:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
                context = await browser.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
                results = await self._execute_scrape(
                    context, url, query, ciudad, limit=max_results,
                    lead_callback=l_callback, stop_check=stop_check,
                    hunter_mode=hunter_mode, known_place_ids=known_place_ids,
                    seen_place_ids=seen_place_ids,
                )
                await browser.close()
                return results

    async def _execute_scrape(
        self, context, url, query, ciudad, limit=20, lead_callback=None,
        stop_check=lambda: False, hunter_mode=False, known_place_ids=None,
        seen_place_ids=None,
    ) -> List[Lead]:
        leads = []
        page = await context.new_page()

        # Optimización extrema: Bloquear recursos visuales innecesarios (imágenes del mapa, fotos de negocios, fuentes)
        async def block_media(route):
            if route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_media)

        try:
            # Ir a la URL
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if stop_check(): return []

            await click_cookie_consent(page, timeout=1000)

            try:
                await page.wait_for_selector(
                    "a.hfpxzc, div[role='article'] > a",
                    timeout=5000,
                )
            except Exception:
                logger.debug(f"GoogleMaps: listado inicial no apareció para {query}")

            if await _is_captcha(page):
                logger.warning(f"CAPTCHA detectado para {query} en {ciudad}")
                return []

            audited = 0
            # Tope de auditoría: evita recorrer el feed entero sin parar cuando
            # hay muchos duplicados que el callback rechaza (p.ej. modo llamada).
            max_audited = max(int(limit) * 5, int(limit) + 60)

            while len(leads) < limit:
                if stop_check(): break

                # Selector más específico: solo el enlace principal que contiene el nombre
                items = await page.query_selector_all("a.hfpxzc")
                if not items:
                    # Fallback si Google cambió la clase, pero evitando capturar todos los 'a'
                    items = await page.query_selector_all("div[role='article'] > a")

                if audited >= len(items):
                    if await _is_end_of_results(page, stop_check=stop_check): break
                    new_count = await _scroll_and_wait(page, len(items), stop_check=stop_check)
                    if new_count == len(items): break
                    continue

                if audited >= max_audited:
                    logger.debug(
                        f"GoogleMaps: límite de auditoría alcanzado "
                        f"({max_audited} resultados revisados, {len(leads)} capturados)"
                    )
                    break

                item = items[audited]
                audited += 1

                place_id = None
                try:
                    name = await item.get_attribute("aria-label")
                    if not name:
                        name = await item.inner_text()

                    if not name: continue

                    # Filtro de basura
                    garbage = ["visitar el sitio web", "cómo llegar", "direcciones", "llamar", "guardar"]
                    if any(g in name.lower() for g in garbage):
                        continue

                    place_url = await item.get_attribute("href")
                    place_id = _extract_place_id(place_url)
                    if not _claim_place_for_scrape(
                        place_url, known_place_ids, seen_place_ids
                    ):
                        logger.debug(f"GoogleMaps: place_id conocido omitido ({place_id})")
                        continue

                    await item.scroll_into_view_if_needed()
                    await item.click(timeout=5000, force=True)
                    if stop_check(): break
                    if not await _wait_for_panel(page, name, stop_check=stop_check):
                        # El panel nunca coincidió con el negocio clickeado:
                        # descartar antes que guardar teléfono/web de otro negocio.
                        logger.warning(f"GoogleMaps: panel no coincide con '{name[:30]}', omitido")
                        if place_id and seen_place_ids is not None:
                            seen_place_ids.discard(place_id)
                        continue

                    # Extracción de datos con selectores robustos
                    # Extraer del atributo href asegura 100% de coincidencia con el negocio (evita desfasaje por carga tardía de SPA)
                    current_url = place_url if place_url else page.url
                    try:
                        await page.wait_for_selector(
                            "div[role='main'] [data-item-id='address'], "
                            "div[role='main'] [data-item-id^='phone:tel:'], "
                            "div[role='main'] [data-item-id='authority']",
                            timeout=2000,
                        )
                    except Exception:
                        pass
                    panel = await page.query_selector(
                        "div[role='main']:has(h1[class*='DUwDvf']), "
                        "div[role='main']:has(div[class*='fontHeadlineLarge'])"
                    )
                    if panel is None:
                        # El panel no coincide con el DOM actual: mejor descartar que
                        # guardar una ficha vacía (sin teléfono, sin web, sin dirección).
                        logger.warning(f"GoogleMaps: panel no encontrado para '{name[:30]}', omitido")
                        if place_id and seen_place_ids is not None:
                            seen_place_ids.discard(place_id)
                        continue

                    # !3d/!4d son las coordenadas DEL NEGOCIO; @lat,lng es solo
                    # el centro del mapa (idéntico para todos los resultados).
                    lat, lng = _extract_place_coordinates(current_url)

                    w_url = None
                    for sel in _WEB_SELECTORS:
                        w_btn = await _panel_element(page, panel, sel)
                        if w_btn:
                            w_url = await w_btn.get_attribute("href")
                            if w_url:
                                # LIMPIEZA DE URL: Ignorar anuncios y redirecciones de Google
                                if w_url.startswith("/") or "google.com/aclk" in w_url or "googleadservices.com" in w_url:
                                    w_url = None
                                    continue
                                break

                    phone = "N/A"
                    for selector in _PHONE_SELECTORS:
                        phone_element = await _panel_element(page, panel, selector)
                        if not phone_element:
                            continue
                        item_id, aria_label, inner_text = await _element_values(phone_element)
                        phone_candidate = _extract_phone_candidate(
                            item_id, aria_label, inner_text
                        )
                        if phone_candidate:
                            phone = clean_phone_number(phone_candidate)
                            if phone != "N/A":
                                break

                    rating = None
                    for selector in _RATING_SELECTORS:
                        rating_element = await _panel_element(page, panel, selector)
                        _, aria_label, inner_text = await _element_values(rating_element)
                        rating = _parse_rating(aria_label, inner_text)
                        if rating is not None:
                            break

                    reviews = 0
                    reviews_found = False
                    for selector in _REVIEW_SELECTORS:
                        review_element = await _panel_element(page, panel, selector)
                        _, aria_label, inner_text = await _element_values(review_element)
                        parsed_reviews = _parse_review_count(aria_label, inner_text)
                        if parsed_reviews is not None:
                            reviews = parsed_reviews
                            reviews_found = True
                            break

                    address = None
                    for selector in _ADDRESS_SELECTORS:
                        address_element = await _panel_element(page, panel, selector)
                        _, aria_label, inner_text = await _element_values(address_element)
                        address = (inner_text or aria_label).strip()
                        for prefix in ("Dirección:", "Address:"):
                            if address.casefold().startswith(prefix.casefold()):
                                address = address[len(prefix):].strip()
                        if address:
                            break

                    maps_category = None
                    for selector in _TYPE_SELECTORS:
                        category_element = await _panel_element(page, panel, selector)
                        _, aria_label, inner_text = await _element_values(category_element)
                        maps_category = (inner_text or aria_label).strip() or None
                        if maps_category:
                            break

                    # Limpieza final de ciudad si viene como coord:
                    final_city = ciudad
                    if ciudad.startswith("coord:"):
                        # Intentamos extraer un nombre de ciudad razonable o dejamos el original
                        # pero el orquestador ya debería encargarse de esto.
                        # Aquí lo dejamos por seguridad.
                        pass

                    if hunter_mode and w_url:
                        logger.info(f"⏭️ GoogleMaps hunter: Omitido {name[:20]}...")
                        continue

                    field_status = {
                        "phone": "found" if phone != "N/A" else "not_found_in_panel",
                        "website": "found" if w_url else "not_found_in_panel",
                        "rating": "found" if rating is not None else "not_found_in_panel",
                        "reviews": "found" if reviews_found else "not_found_in_panel",
                        "address": "found" if address else "not_found_in_panel",
                    }
                    lead_obj = Lead(
                        nombre=name.strip(),
                        ciudad=final_city,
                        nicho=query,
                        fuente="google_maps",
                        telefono=phone,
                        sitio_web=w_url,
                        tiene_web=bool(w_url),
                        direccion=address,
                        rating=rating,
                        reseñas=reviews,
                        maps_url=current_url,
                        lat=lat,
                        lng=lng,
                        raw_data={
                            "maps_url": current_url,
                            "maps_category": maps_category,
                            "field_status": field_status,
                        },
                    )

                    # NOTIFICAR CAPTURA EN TIEMPO REAL
                    accepted = lead_callback(lead_obj) if lead_callback else True
                    if accepted is not True:
                        continue
                    leads.append(lead_obj)
                    logger.info(f"GoogleMaps: Capturado {name[:20]}...")
                except Exception as exc:
                    if place_id and seen_place_ids is not None:
                        seen_place_ids.discard(place_id)
                    logger.debug(f"GoogleMaps: ficha omitida por error de extracción: {exc}")
                    continue
        finally:
            await page.close()
        return leads

    def calificar(self, lead: Lead) -> str:
        if not lead.sitio_web:
            if lead.rating and lead.rating >= 4.2:
                return "oro"
        return "bueno"

import asyncio
import random
import re
import urllib.parse
import streamlit as st
import playwright_stealth
from playwright.async_api import async_playwright
from db import save_lead, open_conn, save_search_history, load_known_identifiers


# ── Constantes ────────────────────────────────────────────────────────────────

MAX_CONCURRENT = 5

BROWSER_ARGS = [
    '--no-sandbox', 
    '--disable-setuid-sandbox', 
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-blink-features=AutomationControlled',
    '--disable-features=IsolateOrigins,site-per-process',
    '--dns-prefetch-disable',
    '--no-first-run',
]

_RATING_SELECTORS = [
    "span[aria-label*='estrellas']", "span[aria-label*='stars']",
    "span[aria-label*='estrelas']",  "span[aria-label*='étoiles']",
    "span[aria-label*='Sterne']",
]
_REVIEW_SELECTORS = [
    "button[aria-label*='reseñas']",    "button[aria-label*='reviews']",
    "button[aria-label*='avaliações']", "button[aria-label*='avis']",
    "button[aria-label*='Rezensionen']",
]
_WEB_SELECTORS = [
    "a[data-item-id='authority']",
    "a[aria-label*='Sitio web']",
    "a[data-value='Sitio web']",
    "a[data-item-id*='authority']",
]
_TYPE_SELECTORS = [
    'button[class*="Dener"]',
    'button[jsaction*="category"]',
    'button[class*="DkEaL"]',
]
# Selectores que indican que el panel lateral cargó el negocio correcto
_PANEL_LOADED_SELECTORS = [
    "h1.DUwDvf", "h1[class*='DUwDvf']", "div[class*='fontHeadlineLarge']",
]
# Indicadores de fin de resultados en Google Maps
_NO_MORE_SELECTORS = [
    "span.HlvSq",                      # "Se muestran todos los resultados"
    "p.fontBodyMedium span",            # variante
    "div[class*='section-no-result']",  # sin resultados
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_place_id(url: str) -> str | None:
    """Extrae el CID de Google Maps (0xHEX:0xHEX) de la URL del lugar."""
    m = re.search(r'!1s(0x[0-9a-fA-F]+:[0-9a-fA-F]+)', url)
    return m.group(1) if m else None


async def _wait_for_panel(page, name: str, timeout_ms: int = 4000, stop_check=lambda: False):
    """Espera a que el panel lateral cargue el negocio. Fallback a sleep."""
    for sel in _PANEL_LOADED_SELECTORS:
        if stop_check(): return
        try:
            await page.wait_for_selector(sel, timeout=timeout_ms)
            return
        except Exception:
            continue
    if not stop_check():
        await asyncio.sleep(1.0)   # fallback


async def _is_captcha(page) -> bool:
    url = page.url
    if any(x in url for x in ("sorry/index", "consent.google", "recaptcha")):
        return True
    el = await page.query_selector('iframe[src*="recaptcha"], #captcha, form#captcha-form')
    return el is not None


async def _scroll_and_wait(page, current_count: int, max_wait: float = 5.0, stop_check=lambda: False) -> int:
    """
    Hace scroll en el feed y espera de forma reactiva hasta que aparezcan
    nuevos items (o se alcance max_wait segundos). Retorna el nuevo total.
    """
    feed = await page.query_selector("div[role='feed']")
    if not feed:
        return current_count
    await feed.evaluate("el => el.scrollBy(0, 1800)")
    t0 = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < max_wait:
        if stop_check(): break
        await asyncio.sleep(0.4)
        new_items = await page.query_selector_all("a.hfpxzc")
        if len(new_items) > current_count:
            return len(new_items)
    return current_count


async def _is_end_of_results(page, stop_check=lambda: False) -> bool:
    """Detecta si Google Maps indica que no hay más resultados."""
    for sel in _NO_MORE_SELECTORS:
        if stop_check(): break
        try:
            el = await page.query_selector(sel)
            if el:
                txt = (await el.inner_text()).lower()
                if any(k in txt for k in ("todos los result", "no result", "no hay result",
                                           "no se encontr", "no more", "end of result")):
                    return True
        except Exception as e:
            # Silencio esperado si no hay indicador de fin, pero logueamos para debug
            pass
    return False


# ── Función principal de zona ─────────────────────────────────────────────────

async def scrape_zone(context, query, max_results, city, country, nicho_val,
                      infinito, modo_escaneo, log_area, live_counter, db_conn, db_lock,
                      known_names: set, known_place_ids: set, seen_run: set):
    """
    Raspa una zona/query de Google Maps.

    Pre-filtrado de 3 niveles:
      1. Nombre (aria-label) contra known_names + seen_run  → salta SIN hacer clic
      2. Place ID (CID extraído de la URL) contra known_place_ids → salta sin guardar
      3. INSERT OR IGNORE en DB → detecta duplicado en el commit final

    Mejoras de scroll: reactivo (espera items nuevos, no sleep fijo).
    Mejoras de carga: wait_for_selector del panel antes de extraer datos.
    """
    page = await context.new_page()
    try:
        if hasattr(playwright_stealth, 'stealth_async'):
            await playwright_stealth.stealth_async(page)
        elif hasattr(playwright_stealth, 'stealth') and callable(playwright_stealth.stealth):
            try:
                await playwright_stealth.stealth(page)
            except Exception:
                playwright_stealth.stealth(page)
    except Exception as e:
        log_area.write(f"Sigilo no aplicado ({e})")

    found, audited, skipped_dupes = 0, 0, 0

    try:
        # Construir URL de búsqueda
        if query.startswith("coord:"):
            _, coords_str = query.split(":", 1)
            clat, clng, czoom = coords_str.split(",")
            goto_url = (f"https://www.google.com/maps/search/"
                        f"{urllib.parse.quote(nicho_val)}/@{clat},{clng},{czoom}z?hl=es")
        else:
            goto_url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}/?hl=es"

        await page.goto(goto_url, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.click('button:has-text("Aceptar")', timeout=5000)
        except Exception:
            # Es normal que no aparezca el botón de Aceptar en todas las cargas
            pass

        if await _is_captcha(page):
            log_area.write(f"CAPTCHA detectado en «{query}» — zona omitida")
            return found, skipped_dupes

        while (infinito or found < max_results) and not st.session_state.stop_requested:

            items = await page.query_selector_all("a.hfpxzc")
            n_items = len(items)

            # ── Scroll reactivo cuando se agotan los items visibles ────────────
            if audited >= n_items:
                if await _is_end_of_results(page):
                    log_area.write(f"Fin de resultados en «{query}»")
                    break
                new_count = await _scroll_and_wait(page, n_items)
                if new_count == n_items:
                    break   # no aparecieron items nuevos → realmente se acabó
                continue

            item  = items[audited]
            audited += 1

            # ── NIVEL 1: pre-filtro por nombre (sin hacer clic) ───────────────
            try:
                name = await item.get_attribute("aria-label")
            except Exception:
                continue
            if not name:
                continue

            name_key = name.lower().strip()
            if name_key in seen_run or name_key in known_names:
                skipped_dupes += 1
                st.session_state.skipped_session = st.session_state.get('skipped_session', 0) + 1
                continue   # salta SIN clic — ahorra tiempo significativo

            # Reclamar el nombre inmediatamente (antes del primer await)
            # para que otras zonas concurrentes no lo procesen en paralelo
            seen_run.add(name_key)

            # ── Click + carga de panel ─────────────────────────────────────────
            _last_err = None
            for _attempt in range(3):
                if st.session_state.stop_requested:
                    break
                if _attempt > 0:
                    await asyncio.sleep(_attempt * 1.5)
                    log_area.write(f"Reintento {_attempt}/2 — {name}")
                try:
                    await item.scroll_into_view_if_needed()
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    try:
                        await item.click(timeout=5000, force=True)
                    except Exception:
                        await item.evaluate("el => el.click()")

                    # Esperar a que el panel cargue de forma explícita
                    await _wait_for_panel(page, name)

                    maps_url = page.url

                    # ── NIVEL 2: pre-filtro por Place ID ─────────────────────
                    place_id = _extract_place_id(maps_url)
                    if place_id and place_id in known_place_ids:
                        skipped_dupes += 1
                        st.session_state.skipped_session = st.session_state.get('skipped_session', 0) + 1
                        log_area.write(f"Place ID conocido, saltando: {name}")
                        _last_err = None
                        break
                    if place_id:
                        known_place_ids.add(place_id)

                    # ── Filtro de modo (tiene/no tiene web) ───────────────────
                    w_url = "Sin sitio web"
                    try:
                        for sel in _WEB_SELECTORS:
                            w_btn = await page.query_selector(sel)
                            if w_btn:
                                raw = await w_btn.get_attribute("href")
                                if raw:
                                    w_url = raw
                                break
                    except Exception:
                        # Error silencioso en extracción de campos opcionales del panel lateral
                        pass

                    tiene_w = w_url != "Sin sitio web"
                    if ("Caza-Sitios" in modo_escaneo and tiene_w) or \
                       ("SEO Audit"   in modo_escaneo and not tiene_w):
                        break

                    # ── Coordenadas GPS (URL ya estabilizada tras panel load) ──
                    lat, lng = None, None
                    m_coord = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                    if m_coord:
                        lat, lng = float(m_coord.group(1)), float(m_coord.group(2))
                    else:
                        # esperar a que la URL se actualice (máx 2s)
                        for _ in range(4):
                            await asyncio.sleep(0.5)
                            m_coord = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                            if m_coord:
                                lat, lng = float(m_coord.group(1)), float(m_coord.group(2))
                                break

                    # ── Teléfono ──────────────────────────────────────────────
                    phone = "N/A"
                    p_el = await page.query_selector('button[data-item-id^="phone:tel:"]')
                    if p_el:
                        phone = await p_el.inner_text()
                    else:
                        # fallback: buscar cualquier botón con "tel:" en aria-label
                        p_el2 = await page.query_selector('[aria-label*="tel:"], [data-tooltip*="tel:"]')
                        if p_el2:
                            phone = (await p_el2.get_attribute("aria-label") or "N/A").replace("tel:", "").strip()

                    # ── Rating y reseñas ──────────────────────────────────────
                    r_num, rev_num = "N/A", "0"
                    try:
                        for _rs in _RATING_SELECTORS:
                            r_el = await page.query_selector(_rs)
                            if r_el:
                                r_raw = await r_el.get_attribute("aria-label") or ""
                                m_r   = re.search(r"(\d[,\.]\d)", r_raw)
                                if m_r:
                                    r_num = f"{m_r.group(1).replace(',', '.')} / 5"
                                break
                        for _rvs in _REVIEW_SELECTORS:
                            rev_el = await page.query_selector(_rvs)
                            if rev_el:
                                rev_raw = await rev_el.get_attribute("aria-label") or ""
                                rev_num = "".join(filter(str.isdigit, rev_raw)) or "0"
                                break
                    except Exception:
                        # Error silencioso en extracción de campos opcionales del panel lateral
                        pass

                    # ── Tipo / Categoría ──────────────────────────────────────
                    tipo_txt = nicho_val
                    for _sel in _TYPE_SELECTORS:
                        _el = await page.query_selector(_sel)
                        if _el:
                            _txt = await _el.inner_text()
                            if _txt and _txt.strip():
                                tipo_txt = _txt.strip()
                                break

                    # ── NIVEL 3: INSERT OR IGNORE en DB ───────────────────────
                    async with db_lock:
                        is_new = save_lead({
                            "Nombre": name, "Teléfono": phone, "Rating": r_num,
                            "Reseñas": rev_num, "Tipo": tipo_txt, "Lat": lat, "Lng": lng,
                            "Zona": query, "Ciudad": city, "Pais": country,
                            "Nicho": nicho_val, "Web": w_url, "Maps_URL": maps_url,
                        }, db_conn)
                        db_conn.commit()

                    if is_new:
                        found += 1
                        st.session_state.total_session += 1
                        known_names.add(name_key)     # actualizar para zonas futuras
                        log_area.write(f"Capturado: {name}")
                    else:
                        skipped_dupes += 1
                        st.session_state.skipped_session = st.session_state.get('skipped_session', 0) + 1
                        log_area.write(f"Duplicado omitido: {name}")

                    # ── Actualizar contador live ──────────────────────────────
                    live_counter.markdown(
                        f"<div style='background:#0C0C0E;border:2px solid #FF0000;border-radius:16px;"
                        f"padding:24px 20px;text-align:center;box-shadow:0 0 25px rgba(255,0,0,0.3);"
                        f"margin-bottom:12px;position:relative;overflow:hidden;'>"
                        f"<div style='position:absolute;top:0;left:0;width:100%;height:4px;background:#FF0000;'></div>"
                        f"<div style='font-family:\"Space Grotesk\",sans-serif;font-size:0.65rem;"
                        f"font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:#6A6A7A;"
                        f"margin-bottom:6px;'>Captura en vivo</div>"
                        f"<div style='font-family:\"Space Grotesk\",sans-serif;font-size:4rem;"
                        f"font-weight:800;color:#FF0000;line-height:1;text-shadow:0 0 15px rgba(255,0,0,0.4);'>"
                        f"{st.session_state.total_session}</div>"
                        f"<div style='font-family:\"Space Grotesk\",sans-serif;font-size:0.75rem;"
                        f"font-weight:600;color:#888;letter-spacing:0.1em;margin-top:4px;'>leads nuevos</div>"
                        f"<div style='margin-top:10px;padding-top:10px;border-top:1px solid #1E1E28;"
                        f"font-family:\"Space Grotesk\",sans-serif;font-size:0.7rem;color:#555568;'>"
                        f"<span style='color:#6A6A7A;'>{st.session_state.get('skipped_session',0)}</span>"
                        f" duplicados omitidos</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    _last_err = None
                    break

                except Exception as _e:
                    _last_err = _e

            if _last_err:
                log_area.write(f"Descartado «{name}» tras 3 intentos: {_last_err}")

    finally:
        await page.close()
        return found, skipped_dupes


# ── Loop principal ────────────────────────────────────────────────────────────

async def main_loop(n, city_base, p, barrios_list, max_r, infinito, modo_escaneo,
                    log_area, NICHOS_DICT, live_counter, progress_bar, extra_terms=None):

    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(headless=True, args=BROWSER_ARGS)
        except Exception as e:
            import traceback
            msg = f"Error crítico al iniciar navegador: {e}\n\n{traceback.format_exc()}"
            st.session_state.error_msg = msg
            raise RuntimeError(msg)

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ),
            viewport={'width': 1280, 'height': 720},
        )
        db_conn = open_conn()
        db_lock = asyncio.Lock()

        try:
            # ── Cargar identificadores ya conocidos (una sola vez) ────────────
            known_names, known_place_ids = load_known_identifiers(city_base, db_conn)
            log_area.write(
                f"Base cargada: {len(known_names)} negocios conocidos en {city_base} · "
                f"{len(known_place_ids)} place IDs totales"
            )

            # Conjunto compartido entre zonas para esta sesión
            seen_run: set = set()

            # ── Construir lista de búsquedas ──────────────────────────────────
            if n == "MODO_EXHAUSTIVO_TOTAL":
                search_list = sorted({x for sub in NICHOS_DICT.values() for x in sub if "TODOS" not in x})
            elif n.startswith("SECTOR_"):
                search_list = [x for x in NICHOS_DICT[n.replace("SECTOR_", "")] if "TODOS" not in x]
            else:
                search_list = [n] + (extra_terms or [])

            all_zones   = [(b, ni) for b in barrios_list for ni in search_list]
            total_tasks = len(all_zones)
            done        = [0]
            sem         = asyncio.Semaphore(MAX_CONCURRENT)

            async def _run_zone(b, ni):
                async with sem:
                    if st.session_state.stop_requested:
                        return (0, 0)
                    if b.startswith("coord:"):
                        query = b
                        label = f"GPS {b.split(':')[1]}"
                    else:
                        query = f"{ni} en {b}, {city_base}, {p}" if b else f"{ni} en {city_base}, {p}"
                        label = b or city_base
                    done[0] += 1
                    pct = max(1, int(done[0] / total_tasks * 100)) if total_tasks else 1
                    progress_bar.progress(pct, text=f"{done[0]}/{total_tasks} — {ni} · {label}")
                    log_area.write(f"Escaneando: {ni} @ {label}")
                    found, dupes = await scrape_zone(
                        context, query, max_r, city_base, p, ni,
                        infinito, modo_escaneo, log_area, live_counter, db_conn, db_lock,
                        known_names, known_place_ids, seen_run,
                    )
                    async with db_lock:
                        save_search_history(city_base, p, ni, label, found, dupes, db_conn)
                    return (found, dupes)

            results      = await asyncio.gather(*[_run_zone(b, ni) for b, ni in all_zones], return_exceptions=True)
            leads_sesion = sum(r[0] for r in results if isinstance(r, tuple))
            dupes_sesion = sum(r[1] for r in results if isinstance(r, tuple))
            progress_bar.progress(100, text="Escaneo completado")
            st.session_state.last_summary = {'leads': leads_sesion, 'dupes': dupes_sesion}

        except Exception as e:
            import traceback
            st.error(f"Error durante el escaneo: {e}")
            st.code(traceback.format_exc())
        finally:
            db_conn.close()
            try:
                await browser.close()
            except Exception:
                # El navegador puede estar ya cerrado
                pass

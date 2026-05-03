import asyncio
import re
import urllib.parse
from typing import List
from playwright.async_api import async_playwright
from sources.base_source import BaseSource, Lead
from scraper import (
    BROWSER_ARGS, _RATING_SELECTORS, _REVIEW_SELECTORS, 
    _WEB_SELECTORS, _TYPE_SELECTORS, _PANEL_LOADED_SELECTORS,
    _wait_for_panel, _is_captcha, _scroll_and_wait, _is_end_of_results
)

class GoogleMapsSource(BaseSource):
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        """
        Implementación completa del scraper de Google Maps.
        """
        if ciudad.startswith("coord:"):
            _, coords_str = ciudad.split(":", 1)
            clat, clng, czoom = coords_str.split(",")
            url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}/@{clat},{clng},{czoom}z?hl=es"
        else:
            search_query = f"{query} en {ciudad}"
            url = f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}/?hl=es"
        
        # Extraer parámetros de control
        browser_context = kwargs.pop("context", None)
        max_results = kwargs.pop("limit", 20)
        l_callback = kwargs.pop("lead_callback", None)
        stop_check = kwargs.pop("stop_check", lambda: False)
        
        if browser_context:
            return await self._execute_scrape(browser_context, url, query, ciudad, limit=max_results, lead_callback=l_callback, stop_check=stop_check)
        else:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
                context = await browser.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
                results = await self._execute_scrape(context, url, query, ciudad, limit=max_results, lead_callback=l_callback, stop_check=stop_check)
                await browser.close()
                return results

    async def _execute_scrape(self, context, url, query, ciudad, limit=20, lead_callback=None, stop_check=lambda: False) -> List[Lead]:
        leads = []
        page = await context.new_page()
        try:
            # Ir a la URL
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if stop_check(): return []
            
            try: await page.click('button:has-text("Aceptar")', timeout=3000)
            except Exception: pass

            if await _is_captcha(page):
                print(f"🛑 CAPTCHA detectado para {query} en {ciudad}")
                return []

            audited = 0
            
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

                item = items[audited]
                audited += 1

                try:
                    name = await item.get_attribute("aria-label")
                    if not name: 
                        name = await item.inner_text()
                    
                    if not name: continue
                    
                    # Filtro de basura
                    garbage = ["visitar el sitio web", "cómo llegar", "direcciones", "llamar", "guardar"]
                    if any(g in name.lower() for g in garbage):
                        continue
                    
                    await item.scroll_into_view_if_needed()
                    await item.click(timeout=5000, force=True)
                    if stop_check(): break
                    await _wait_for_panel(page, name, stop_check=stop_check)
                    
                    # Extracción de datos con selectores robustos
                    current_url = page.url
                    lat, lng = None, None
                    m_coord = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", current_url)
                    if m_coord:
                        lat, lng = float(m_coord.group(1)), float(m_coord.group(2))

                    w_url = None
                    for sel in _WEB_SELECTORS:
                        w_btn = await page.query_selector(sel)
                        if w_btn:
                            w_url = await w_btn.get_attribute("href")
                            if w_url:
                                # LIMPIEZA DE URL: Ignorar anuncios y redirecciones de Google
                                if w_url.startswith("/") or "google.com/aclk" in w_url or "googleadservices.com" in w_url:
                                    w_url = None
                                    continue
                                break

                    phone = "N/A"
                    p_el = await page.query_selector('button[data-item-id^="phone:tel:"]')
                    if p_el: 
                        phone = await p_el.inner_text()
                    else:
                        # Fallback de teléfono
                        p_el2 = await page.query_selector('button[aria-label*="Llamar"]')
                        if p_el2:
                            phone_raw = await p_el2.get_attribute("aria-label")
                            m_p = re.search(r"(\+?\d[\d\s-]{7,})", phone_raw)
                            if m_p: phone = m_p.group(1).strip()

                    rating = None
                    for _rs in _RATING_SELECTORS:
                        r_el = await page.query_selector(_rs)
                        if r_el:
                            r_raw = await r_el.get_attribute("aria-label") or ""
                            m_r = re.search(r"(\d[,\.]\d)", r_raw)
                            if m_r: rating = float(m_r.group(1).replace(',', '.'))
                            break
                    
                    reviews = 0
                    for _rvs in _REVIEW_SELECTORS:
                        rv_el = await page.query_selector(_rvs)
                        if rv_el:
                            rv_raw = await rv_el.get_attribute("aria-label") or ""
                            m_rv = re.search(r"(\d+)", rv_raw.replace('.', '').replace(',', ''))
                            if m_rv: reviews = int(m_rv.group(1))
                            break

                    lead_obj = Lead(
                        nombre=name.strip(),
                        ciudad=ciudad,
                        nicho=query,
                        fuente="google_maps",
                        telefono=phone,
                        sitio_web=w_url,
                        tiene_web=bool(w_url),
                        rating=rating,
                        reseñas=reviews,
                        maps_url=current_url,
                        lat=lat,
                        lng=lng,
                        raw_data={"maps_url": current_url, "reviews_raw": reviews}
                    )
                    leads.append(lead_obj)
                    
                    # NOTIFICAR CAPTURA EN TIEMPO REAL
                    if lead_callback: lead_callback(lead_obj)
                    print(f"✅ GoogleMaps: Capturado {name[:20]}...")
                except Exception:
                    continue # Sigue con el siguiente
        finally:
            await page.close()
        return leads

    def calificar(self, lead: Lead) -> str:
        if not lead.sitio_web:
            if lead.rating and lead.rating >= 4.2:
                return "oro"
        return "bueno"


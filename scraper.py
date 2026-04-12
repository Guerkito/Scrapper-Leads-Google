import asyncio
import re
import urllib.parse
import streamlit as st
import playwright_stealth
from playwright.async_api import async_playwright
from db import save_lead, open_conn

MAX_CONCURRENT = 3  # páginas simultáneas máximas

BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--no-zygote',
    '--single-process',
    '--disable-blink-features=AutomationControlled',
    '--disable-extensions',
    '--disable-infobars',
    '--disable-browser-side-navigation',
    '--disable-features=IsolateOrigins,site-per-process',
]

_RATING_SELECTORS = [
    "span[aria-label*='estrellas']",   # es
    "span[aria-label*='stars']",        # en
    "span[aria-label*='estrelas']",     # pt
    "span[aria-label*='étoiles']",      # fr
    "span[aria-label*='Sterne']",       # de
]
_REVIEW_SELECTORS = [
    "button[aria-label*='reseñas']",    # es
    "button[aria-label*='reviews']",    # en
    "button[aria-label*='avaliações']", # pt
    "button[aria-label*='avis']",       # fr
    "button[aria-label*='Rezensionen']",# de
]
_WEB_SELECTORS = [
    "a[data-item-id='authority']",
    "a[aria-label*='Sitio web']",
    "a[data-value='Sitio web']",
]
_TYPE_SELECTORS = [
    'button[class*="Dener"]',
    'button[jsaction*="category"]',
    'button[class*="DkEaL"]',
]


async def scrape_zone(context, query, max_results, city, country, nicho_val,
                       infinito, modo_escaneo, log_area, live_counter, db_conn):
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
        log_area.write(f"⚠️ Sigilo no aplicado ({e})")

    found, audited = 0, 0
    try:
        await page.goto(
            f"https://www.google.com/maps/search/{urllib.parse.quote(query)}/?hl=es",
            wait_until="domcontentloaded", timeout=60000,
        )
        try:
            await page.click('button:has-text("Aceptar")', timeout=5000)
        except Exception:
            pass

        while (infinito or found < max_results) and not st.session_state.stop_requested:
            if st.session_state.stop_requested:
                break

            items = await page.query_selector_all("a.hfpxzc")
            if audited >= len(items):
                feed = await page.query_selector("div[role='feed']")
                if feed:
                    await feed.evaluate("el => el.scrollBy(0, 1500)")
                    await asyncio.sleep(2)
                    new_items = await page.query_selector_all("a.hfpxzc")
                    if len(new_items) == len(items):
                        break
                    continue
                else:
                    break

            item = items[audited]
            audited += 1

            # Reintentos con backoff exponencial (0s → 1s → 2s)
            _last_err = None
            for _attempt in range(3):
                if st.session_state.stop_requested:
                    break
                if _attempt > 0:
                    await asyncio.sleep(_attempt)
                    log_area.write(f"🔄 Reintento {_attempt}/2 — elemento {audited}...")
                try:
                    name = await item.get_attribute("aria-label")
                    if not name:
                        break
                    await item.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    try:
                        await item.click(timeout=5000, force=True)
                    except Exception:
                        await item.evaluate("el => el.click()")
                    await asyncio.sleep(1)

                    maps_url = page.url
                    w_url = "Sin sitio web"
                    try:
                        for sel in _WEB_SELECTORS:
                            w_btn = await page.query_selector(sel)
                            if w_btn:
                                raw = await w_btn.get_attribute("href")
                                w_url = raw if raw else "Sin sitio web"
                                break
                    except Exception:
                        pass

                    tiene_w = w_url != "Sin sitio web"
                    if ("Caza-Sitios" in modo_escaneo and tiene_w) or \
                       ("SEO Audit" in modo_escaneo and not tiene_w):
                        log_area.write(f"⏭️ Saltado: {name}")
                        break

                    lat, lng = None, None
                    for _ in range(5):
                        m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                        if m:
                            lat, lng = float(m.group(1)), float(m.group(2))
                            break
                        await asyncio.sleep(0.5)

                    p_el = await page.query_selector('button[data-item-id^="phone:tel:"]')
                    phone = await p_el.inner_text() if p_el else "N/A"

                    r_num, rev_num = "N/A", "0"
                    try:
                        for _rs in _RATING_SELECTORS:
                            r_el = await page.query_selector(_rs)
                            if r_el:
                                r_raw = await r_el.get_attribute("aria-label")
                                m_r = re.search(r"(\d[,\.]\d)", r_raw)
                                if m_r:
                                    r_num = f"{m_r.group(1).replace(',', '.')} / 5"
                                break
                        for _rvs in _REVIEW_SELECTORS:
                            rev_el = await page.query_selector(_rvs)
                            if rev_el:
                                rev_raw = await rev_el.get_attribute("aria-label")
                                rev_num = "".join(filter(str.isdigit, rev_raw)) or "0"
                                break
                    except Exception:
                        pass

                    tipo_txt = nicho_val
                    for _sel in _TYPE_SELECTORS:
                        _el = await page.query_selector(_sel)
                        if _el:
                            _txt = await _el.inner_text()
                            if _txt and _txt.strip():
                                tipo_txt = _txt.strip()
                                break

                    save_lead({
                        "Nombre": name, "Teléfono": phone, "Rating": r_num,
                        "Reseñas": rev_num, "Tipo": tipo_txt, "Lat": lat, "Lng": lng,
                        "Zona": query, "Ciudad": city, "Pais": country,
                        "Nicho": nicho_val, "Web": w_url, "Maps_URL": maps_url,
                    }, db_conn)
                    db_conn.commit()
                    found += 1
                    st.session_state.total_session += 1
                    live_counter.markdown(
                        f"<div style='background:#111;border:2px solid #39FF14;border-radius:15px;"
                        f"padding:15px;text-align:center'>"
                        f"<h1 style='margin:0;color:#39FF14'>{st.session_state.total_session} LEADS</h1>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    log_area.write(f"✅ CAPTURADO: {name}")
                    _last_err = None
                    break
                except Exception as _e:
                    _last_err = _e

            if _last_err:
                log_area.write(f"⚠️ Descartado elemento {audited} tras 3 intentos: {_last_err}")
    finally:
        await page.close()
        return found


async def main_loop(n, city_base, p, barrios_list, max_r, infinito, modo_escaneo,
                    log_area, NICHOS_DICT, live_counter, progress_bar):
    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(headless=True, args=BROWSER_ARGS)
        except Exception as e:
            import traceback
            st.session_state.error_msg = (
                f"❌ ERROR CRÍTICO AL INICIAR NAVEGADOR: {e}\n\nDetalles:\n{traceback.format_exc()}"
            )
            return

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720},
        )
        db_conn = open_conn()

        try:
            # Construir lista completa de búsquedas
            if n == "MODO_EXHAUSTIVO_TOTAL":
                search_list = sorted({x for sub in NICHOS_DICT.values() for x in sub if "TODOS" not in x})
            elif n.startswith("SECTOR_"):
                search_list = [x for x in NICHOS_DICT[n.replace("SECTOR_", "")] if "TODOS" not in x]
            else:
                search_list = [n]

            all_zones = [(b, ni) for b in barrios_list for ni in search_list]
            total_tasks = len(all_zones)
            done = [0]  # lista mutable para cerrar sobre ella en la closure
            sem = asyncio.Semaphore(MAX_CONCURRENT)

            async def _run_zone(b, ni):
                async with sem:
                    if st.session_state.stop_requested:
                        return 0
                    query = f"{ni} en {b}, {city_base}, {p}" if b else f"{ni} en {city_base}, {p}"
                    result = await scrape_zone(
                        context, query, max_r, city_base, p, ni,
                        infinito, modo_escaneo, log_area, live_counter, db_conn,
                    )
                    done[0] += 1
                    pct = int(done[0] / total_tasks * 100) if total_tasks else 0
                    progress_bar.progress(
                        pct,
                        text=f"🔎 {done[0]}/{total_tasks} — {ni}" + (f" · {b}" if b else ""),
                    )
                    return result

            # Lanzar todas las zonas en paralelo (limitado por semáforo a MAX_CONCURRENT)
            results = await asyncio.gather(
                *[_run_zone(b, ni) for b, ni in all_zones],
                return_exceptions=True,
            )
            leads_sesion = sum(r for r in results if isinstance(r, int))
            progress_bar.progress(100, text="✅ Escaneo completado")
            st.session_state.last_summary = {'leads': leads_sesion}

        except Exception as e:
            import traceback
            st.error(f"❌ ERROR DURANTE EL ESCANEO: {e}")
            st.code(traceback.format_exc())
        finally:
            db_conn.close()
            try:
                await browser.close()
            except Exception:
                pass

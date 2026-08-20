import asyncio
import re
import urllib.parse
from typing import List
from playwright.async_api import async_playwright
from loguru import logger
from sources.base_source import BaseSource, Lead
from engine.maps_helpers import dorking_goto, decode_google_url

class TripAdvisorSource(BaseSource):
    """
    Busca restaurantes, hoteles y atracciones en TripAdvisor mediante Google Dorking.
    """
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        search_query = f'site:tripadvisor.co "{query}" "{ciudad}"'
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&hl=es"
        
        external_context = kwargs.pop("context", None)
        l_callback = kwargs.pop("lead_callback", None)
        stop_check = kwargs.pop("stop_check", lambda: False)
        hunter_mode = kwargs.pop("hunter_mode", False)

        if hunter_mode:
            return []

        if external_context:
            return await self._execute_scrape(external_context, url, query, ciudad, l_callback, stop_check, **kwargs)
        else:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
                results = await self._execute_scrape(context, url, query, ciudad, l_callback, stop_check, **kwargs)
                await browser.close()
                return results

    async def _execute_scrape(self, context, url, query, ciudad, lead_callback=None, stop_check=lambda: False, **kwargs) -> List[Lead]:
        leads = []
        page = await context.new_page()
        max_results = kwargs.get("limit", 10)
        
        try:
            if not await dorking_goto(page, url):
                return []
            if stop_check(): return []

            results = await page.query_selector_all("div.g")
            
            for res in results[:max_results]:
                if stop_check(): break
                try:
                    title_el = await res.query_selector("h3")
                    link_el = await res.query_selector("a")
                    snippet_el = await res.query_selector("div.VwiC3b")

                    if title_el and link_el:
                        full_title = await title_el.inner_text()
                        profile_url = await link_el.get_attribute("href")
                        profile_url = decode_google_url(profile_url)
                        snippet = await snippet_el.inner_text() if snippet_el else ""

                        # Filtrar foros, buscamos listados (Restaurant_Review, Hotel_Review)
                        if "ShowTopic" in profile_url or "ShowForum" in profile_url:
                            continue

                        # Limpieza del título
                        name = full_title.split(" - ")[0].split(" | ")[0].strip()
                        
                        # Extraer rating y reviews del snippet
                        rating = None
                        reviews = 0
                        m_rating = re.search(r'Valoración:\s*(\d[,\.]\d)', snippet)
                        if m_rating: rating = float(m_rating.group(1).replace(',', '.'))
                        
                        m_rev = re.search(r'([\d.,]+)\s*opiniones', snippet)
                        if m_rev:
                            # "1.234" / "1,234" usa separador de miles: quedarse con los dígitos.
                            reviews = int("".join(ch for ch in m_rev.group(1) if ch.isdigit()))

                        lead_obj = Lead(
                            nombre=name,
                            ciudad=ciudad,
                            nicho=query,
                            fuente="tripadvisor",
                            perfil_url=profile_url,
                            tiene_web=False,
                            tipo="B2C",
                            sector="turismo_gastronomia",
                            calificacion="bueno",
                            rating=rating,
                            reseñas=reviews,
                            notas="[Encontrado en TripAdvisor]",
                            raw_data={"snippet": snippet, "full_title": full_title}
                        )
                        leads.append(lead_obj)
                        if lead_callback: lead_callback(lead_obj)
                except Exception as e:
                    continue
        except Exception as e:
            logger.warning(f"Error en búsqueda TripAdvisor: {e}")
        finally:
            await page.close()
            
        return leads

    def calificar(self, lead: Lead) -> str:
        return "oro" if lead.rating and lead.rating >= 4.0 and lead.reseñas > 20 else "bueno"

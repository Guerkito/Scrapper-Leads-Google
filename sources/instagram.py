import asyncio
import re
import urllib.parse
from typing import List
from playwright.async_api import async_playwright
from loguru import logger
from sources.base_source import BaseSource, Lead
from engine.maps_helpers import dorking_goto, decode_google_url

class InstagramSource(BaseSource):
    """
    Busca perfiles de empresas en Instagram utilizando Google Dorking.
    Excelente para Moda, Gastronomía y Belleza.
    """
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        search_query = f'site:instagram.com "{query}" "{ciudad}"'
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

                        # Ignorar links de posts, reels o tags, queremos solo perfiles
                        if "/p/" in profile_url or "/reel/" in profile_url or "/explore/" in profile_url:
                            continue

                        # Limpieza del título (ej: "Nombre Empresa (@usuario) • Instagram...")
                        name = full_title.split("(@")[0].strip()
                        
                        # Extraer seguidores del snippet (soporta miles: "1.2k", "2,5 mil", "12.345")
                        followers = 0
                        m_foll = re.search(r'([\d.,]+[kKmM]?)\s*Followers', snippet, re.IGNORECASE)
                        if not m_foll:
                            m_foll = re.search(r'([\d.,]+[kKmM]?)\s*Seguidores', snippet, re.IGNORECASE)
                            
                        if m_foll:
                            f_str = m_foll.group(1).lower().replace(',', '.')
                            if 'k' in f_str:
                                followers = int(float(f_str.replace('k', '')) * 1000)
                            elif 'm' in f_str:
                                followers = int(float(f_str.replace('m', '')) * 1000000)
                            else:
                                followers = int(round(float(f_str)))
                        
                        lead_obj = Lead(
                            nombre=name,
                            ciudad=ciudad,
                            nicho=query,
                            fuente="instagram",
                            perfil_url=profile_url,
                            instagram=profile_url,
                            tiene_web=False, # Consideramos que IG no es una web propia
                            tipo="B2C", # La mayoría en IG son B2C, el orquestador lo reescribe si es B2B
                            calificacion="bueno",
                            reseñas=followers, # Usamos el campo de reseñas para guardar los seguidores
                            notas=f"[Influencia en IG: {followers} seguidores]",
                            raw_data={"snippet": snippet, "followers": followers}
                        )
                        leads.append(lead_obj)
                        if lead_callback: lead_callback(lead_obj)
                except Exception as e:
                    continue
        except Exception as e:
            logger.warning(f"Error en búsqueda Instagram (Google): {e}")
        finally:
            await page.close()
            
        return leads

    def calificar(self, lead: Lead) -> str:
        return "oro" if lead.reseñas and lead.reseñas > 5000 else "bueno"

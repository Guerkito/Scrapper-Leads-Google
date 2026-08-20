import asyncio
import re
import urllib.parse
from typing import List
from scrapling import Fetcher
from loguru import logger
from sources.base_source import BaseSource, Lead, fetcher_get_with_retry
from engine.maps_helpers import decode_google_url

class YelpSource(BaseSource):
    """
    Busca negocios en Yelp utilizando Google Dorking y Scrapling.
    """
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        search_query = f'site:yelp.com "{query}" "{ciudad}"'
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&hl=es"
        
        l_callback = kwargs.pop("lead_callback", None)
        stop_check = kwargs.pop("stop_check", lambda: False)
        max_results = kwargs.get("limit", 10)
        
        leads = []
        try:
            fetcher = Fetcher()
            response = await asyncio.to_thread(fetcher_get_with_retry, fetcher, url)
            
            if response is None:
                return []
            if response.status_code != 200:
                return []

            if any(marker in response.url for marker in ("sorry/index", "consent.google", "recaptcha")):
                logger.warning(f"YelpSource: CAPTCHA/consent de Google detectado para {query}")
                return []

            results = response.css("div.g")
            
            for res in results[:max_results]:
                if stop_check(): break
                try:
                    title = res.css("h3::text").get()
                    link = res.css("a::attr(href)").get()
                    snippet = res.css("div.VwiC3b::text").get() or ""

                    if title and link and "yelp.com/biz" in link:
                        link = decode_google_url(link)
                        if "yelp.com/biz" not in link:
                            continue
                        name = title.split(" - ")[0].split(" | ")[0].strip()
                        
                        # Extraer rating del snippet (Yelp suele mostrarlo)
                        rating = None
                        m_r = re.search(r'Calificación:\s*(\d[,\.]\d)', snippet)
                        if m_r: rating = float(m_r.group(1).replace(',', '.'))
                        
                        lead_obj = Lead(
                            nombre=name,
                            ciudad=ciudad,
                            nicho=query,
                            fuente="yelp",
                            perfil_url=link,
                            tiene_web=False,
                            tipo="B2C",
                            calificacion="bueno",
                            rating=rating,
                            notas=f"[Encontrado en Yelp]",
                            raw_data={"snippet": snippet}
                        )
                        leads.append(lead_obj)
                        if l_callback: l_callback(lead_obj)
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error en YelpSource: {e}")
            
        return leads

    def calificar(self, lead: Lead) -> str:
        return "oro" if lead.rating and lead.rating >= 4.0 else "bueno"

import asyncio
import re
import urllib.parse
from typing import List
from scrapling import Fetcher
from loguru import logger
from sources.base_source import BaseSource, Lead, fetcher_get_with_retry
from engine.maps_helpers import decode_google_url

class GlassdoorSource(BaseSource):
    """
    Busca empresas en Glassdoor utilizando Google Dorking y Scrapling.
    Excelente para identificar empresas con estructura corporativa y presupuesto.
    """
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        search_query = f'site:glassdoor.com/Overview "{query}" "{ciudad}"'
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
                logger.warning(f"GlassdoorSource: CAPTCHA/consent de Google detectado para {query}")
                return []

            results = response.css("div.g")
            
            for res in results[:max_results]:
                if stop_check(): break
                try:
                    title = res.css("h3::text").get()
                    link = res.css("a::attr(href)").get()
                    snippet = res.css("div.VwiC3b::text").get() or ""

                    if title and link and "glassdoor.com" in link:
                        link = decode_google_url(link)
                        name = title.split(" Working at ")[-1].split(" Reviews ")[0].split(" | ")[0].strip()
                        if not name: name = title.split(" - ")[0]

                        lead_obj = Lead(
                            nombre=name,
                            ciudad=ciudad,
                            nicho=query,
                            fuente="glassdoor",
                            perfil_url=link,
                            tiene_web=False,
                            tipo="B2B",
                            sector="corporativo",
                            calificacion="oro", # Glassdoor implica empresa establecida
                            notas=f"[Empresa en Glassdoor - Estructura Corporativa]",
                            raw_data={"snippet": snippet}
                        )
                        leads.append(lead_obj)
                        if l_callback: l_callback(lead_obj)
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error en GlassdoorSource: {e}")
            
        return leads

    def calificar(self, lead: Lead) -> str:
        return "oro"

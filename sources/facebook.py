import asyncio
import re
import urllib.parse
from typing import List
from scrapling import Fetcher
from loguru import logger
from sources.base_source import BaseSource, Lead, fetcher_get_with_retry
from engine.maps_helpers import decode_google_url

class FacebookSource(BaseSource):
    """
    Busca páginas de Facebook de negocios utilizando Google Dorking
    y extrae información mediante Scrapling para mayor indetectabilidad.
    """
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        search_query = f'site:facebook.com "{query}" "{ciudad}"'
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&hl=es"
        
        l_callback = kwargs.pop("lead_callback", None)
        stop_check = kwargs.pop("stop_check", lambda: False)
        max_results = kwargs.get("limit", 10)
        
        leads = []
        try:
            # Usamos Fetcher de Scrapling para obtener el HTML de Google
            # El Fetcher estándar es muy rápido y para Google suele bastar con buenos headers
            fetcher = Fetcher()
            response = await asyncio.to_thread(fetcher_get_with_retry, fetcher, url)
            
            if response is None:
                return []
            if response.status_code != 200:
                logger.warning(f"Error en FacebookSource (Google): Status {response.status_code}")
                return []

            # Google pidió captcha/consentimiento: abortar en vez de asumir "sin resultados"
            if any(marker in response.url for marker in ("sorry/index", "consent.google", "recaptcha")):
                logger.warning(f"FacebookSource: CAPTCHA/consent de Google detectado para {query}")
                return []

            # Usamos el motor de selección de Scrapling (basado en parsel/lxml pero más rápido)
            # Buscamos los bloques de resultados de Google
            results = response.css("div.g")
            
            for res in results[:max_results]:
                if stop_check(): break
                try:
                    title = res.css("h3::text").get()
                    link = res.css("a::attr(href)").get()
                    snippet = res.css("div.VwiC3b::text").get() or ""

                    if title and link and "facebook.com" in link:
                        # La URL viene envuelta en la redireccion de Google; se decodifica primero.
                        link = decode_google_url(link)
                        # Limpieza básica de Facebook URLs (quitar parámetros de tracking)
                        clean_link = link.split("?")[0].split("&")[0]
                        if "facebook.com" not in clean_link:
                            continue
                        
                        # Extraer nombre (ej: "Empresa XYZ - Home | Facebook")
                        name = title.split(" - ")[0].split(" | ")[0].strip()
                        
                        lead_obj = Lead(
                            nombre=name,
                            ciudad=ciudad,
                            nicho=query,
                            fuente="facebook",
                            perfil_url=clean_link,
                            facebook=clean_link,
                            tiene_web=False,
                            tipo="B2C", # Por defecto en FB
                            calificacion="bueno",
                            notas=f"[Encontrado en Facebook]",
                            raw_data={"snippet": snippet, "full_title": title}
                        )
                        leads.append(lead_obj)
                        if l_callback: l_callback(lead_obj)
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error en FacebookSource: {e}")
            
        return leads

    def calificar(self, lead: Lead) -> str:
        return "bueno"

import asyncio
import re
import urllib.parse
from typing import List
from playwright.async_api import async_playwright
from sources.base_source import BaseSource, Lead

class LinkedInSource(BaseSource):
    """
    Busca perfiles de empresas en LinkedIn utilizando motores de búsqueda 
    (Google Dorking) para evitar bloqueos directos y muros de login.
    """
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        search_query = f'site:linkedin.com/company "{query}" "{ciudad}"'
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&hl=es"
        
        external_context = kwargs.pop("context", None)
        l_callback = kwargs.pop("lead_callback", None)
        stop_check = kwargs.pop("stop_check", lambda: False)
        
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
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if stop_check(): return []
            
            # Aceptar cookies si aparece el banner
            try: await page.click('button:has-text("Aceptar")', timeout=2000)
            except Exception: pass

            # Buscamos los contenedores de resultados de Google
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
                        snippet = await snippet_el.inner_text() if snippet_el else ""

                        name = full_title.split(" | ")[0].split(" - ")[0].strip()
                        
                        sector = "Empresarial"
                        if "Industria" in snippet:
                            m = re.search(r"Industria:\s*([^·|\n]+)", snippet)
                            if m: sector = m.group(1).strip()

                        lead_obj = Lead(
                            nombre=name,
                            ciudad=ciudad,
                            nicho=query,
                            fuente="linkedin",
                            sitio_web=profile_url,
                            tipo="B2B",
                            sector=sector,
                            calificacion="bueno",
                            raw_data={"snippet": snippet, "full_title": full_title}
                        )
                        leads.append(lead_obj)
                        if lead_callback: lead_callback(lead_obj)
                except Exception as e:
                    print(f"Error procesando resultado LI: {e}")
                    continue
        except Exception as e:
            print(f"Error en búsqueda LinkedIn (Google): {e}")
        finally:
            await page.close()
            
        return leads

    def calificar(self, lead: Lead) -> str:
        # Empresas en LinkedIn con perfiles establecidos suelen ser B2B interesantes
        return "oro" if lead.tipo == "B2B" else "bueno"

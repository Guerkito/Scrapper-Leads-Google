import urllib.parse
from typing import List
from playwright.async_api import async_playwright
from loguru import logger
from sources.base_source import BaseSource, Lead

class PaginasAmarillasSource(BaseSource):
    BASE_URL = "https://www.paginasamarillas.com.co"
    
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        """
        Scraper para Páginas Amarillas Colombia.
        """
        leads = []
        search_city = ciudad.split(",", 1)[0].strip()
        search_url = (
            f"{self.BASE_URL}/busqueda/"
            f"{urllib.parse.quote(query, safe='')}/"
            f"{urllib.parse.quote(search_city, safe='')}"
        )
        
        external_context = kwargs.pop("context", None)
        l_callback = kwargs.pop("lead_callback", None)
        stop_check = kwargs.pop("stop_check", lambda: False)
        hunter_mode = kwargs.pop("hunter_mode", False)
        max_results = max(1, int(kwargs.pop("limit", 20)))

        if hunter_mode:
            return []

        if external_context:
            return await self._execute_scrape(
                external_context, search_url, query, ciudad, l_callback,
                stop_check, hunter_mode, max_results,
            )
        else:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                results = await self._execute_scrape(
                    context, search_url, query, ciudad, l_callback,
                    stop_check, hunter_mode, max_results,
                )
                await browser.close()
                return results

    async def _execute_scrape(
        self, context, search_url, query, ciudad, lead_callback=None,
        stop_check=lambda: False, hunter_mode=False, limit=20,
    ) -> List[Lead]:
        leads = []
        page = await context.new_page()
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            if stop_check(): return []
            
            # Verificar Bloqueo / Captcha
            content = await page.content()
            if "recaptcha" in content.lower() or "bot-detection" in content.lower():
                logger.warning(f"Páginas Amarillas: Bloqueo por CAPTCHA detectado para {query}")
                return []

            try:
                await page.wait_for_selector(".advert-item", timeout=10000)
            except:
                logger.warning(f"Páginas Amarillas: No se encontraron resultados para {query} en {ciudad}")
                return []
            
            items = await page.query_selector_all(".advert-item")
            for item in items:
                if stop_check(): break
                
                nombre = await item.query_selector(".advert-name")
                nombre_txt = await nombre.inner_text() if nombre else "N/A"
                
                tel_txt = await item.get_attribute("data-phone")
                
                web = await item.query_selector("a.advert-site")
                web_url = await web.get_attribute("href") if web else None

                if hunter_mode and web_url:
                    continue

                lead_obj = Lead(
                    nombre=nombre_txt.strip(),
                    ciudad=ciudad,
                    telefono=tel_txt,
                    sitio_web=web_url,
                    tiene_web=bool(web_url),
                    fuente="paginas_amarillas",
                    nicho=query,
                    raw_data={"fuente": "paginas_amarillas"}
                )
                accepted = lead_callback(lead_obj) if lead_callback else True
                if accepted is not True:
                    continue
                leads.append(lead_obj)
                if len(leads) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Error en Páginas Amarillas: {e}")
        finally:
            await page.close()
        return leads

import asyncio
from playwright.async_api import async_playwright

async def check_google_maps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("Navegando a Google Maps...")
        await page.goto("https://www.google.com/maps/search/restaurantes+en+Madrid", wait_until="domcontentloaded", timeout=60000)
        
        # Esperar un poco a que carguen los elementos clave
        await asyncio.sleep(5)
        
        # Aceptar cookies si aparece el diálogo
        try:
            # Selector más común para el botón de cookies
            cookies_button = await page.query_selector('button[aria-label="Aceptar todo"], button:has-text("Aceptar")')
            if cookies_button:
                await cookies_button.click()
                print("Cookies aceptadas.")
                await asyncio.sleep(2)
        except Exception as e:
            print(f"No se pudo interactuar con el botón de cookies: {e}")

        await asyncio.sleep(5)
        
        # Tomar captura para ver qué ve el bot
        await page.screenshot(path="debug_maps.png")
        print("Captura guardada como debug_maps.png")

        # Buscar los enlaces de los negocios
        links = await page.query_selector_all('a')
        print(f"Se encontraron {len(links)} enlaces en total.")
        
        # Filtrar posibles contenedores de negocios
        for i, link in enumerate(links[:100]):
            href = await link.get_attribute("href")
            if href and "/maps/place/" in href:
                cls = await link.get_attribute("class")
                aria = await link.get_attribute("aria-label")
                print(f"Negocio encontrado: {aria} | Clase: {cls}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_google_maps())

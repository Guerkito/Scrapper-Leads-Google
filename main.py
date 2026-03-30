import asyncio
import pandas as pd
from playwright.async_api import async_playwright
import sys

async def scrape_google_maps(search_query, total_results=50):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Cambiado a True para compatibilidad CLI
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"Buscando: {search_query}")
        await page.goto("https://www.google.com/maps", wait_until="networkidle")
        
        # Aceptar cookies si aparece el diálogo
        try:
            await page.click('button[aria-label="Aceptar todo"]', timeout=5000)
        except:
            pass

        # Buscar
        await page.fill('input#searchboxinput', search_query)
        await page.keyboard.press("Enter")
        await page.wait_for_selector('div[role="feed"]')

        results = []
        processed_count = 0
        
        # Scroll para cargar más resultados
        while len(results) < total_results:
            items = await page.query_selector_all('a.hfpxzc')
            
            if processed_count >= len(items):
                # Intentar hacer scroll en el contenedor del feed
                feed = await page.query_selector('div[role="feed"]')
                if feed:
                    await feed.evaluate('element => element.scrollBy(0, 2000)')
                    await asyncio.sleep(3) # Esperar a que carguen nuevos elementos
                    new_items = await page.query_selector_all('a.hfpxzc')
                    if len(new_items) == len(items):
                        print("No se encontraron más resultados al hacer scroll.")
                        break
                    continue
                else:
                    break

            # Procesar el siguiente item
            item = items[processed_count]
            processed_count += 1
            
            try:
                # Obtener el nombre antes de hacer clic para evitar errores si el DOM cambia
                name = await item.get_attribute('aria-label')
                
                # Hacer scroll hasta el elemento y clic
                await item.scroll_into_view_if_needed()
                await item.click()
                # Esperar explícitamente a que el panel lateral se actualice con el nuevo nombre
                try:
                    await page.wait_for_selector(f'h1.DUwDvf:has-text("{name}")', timeout=5000)
                except:
                    pass # A veces el nombre en el feed es ligeramente distinto al del panel

                # Pequeña pausa para asegurar que los botones de contacto cargan
                await asyncio.sleep(1)

                # Buscar sitio web con reintento corto
                website = None
                for _ in range(2):
                    website_element = await page.query_selector('a[data-item-id="authority"]')
                    if website_element:
                        website = await website_element.get_attribute('href')
                        break
                    await asyncio.sleep(0.5)
                
                # Filtrar: solo si NO tiene sitio web
                if not website:
                    address_element = await page.query_selector('button[data-item-id="address"]')
                    address = await address_element.inner_text() if address_element else "N/A"
                    
                    phone_element = await page.query_selector('button[data-item-id^="phone:tel:"]')
                    phone = await phone_element.inner_text() if phone_element else "N/A"

                    results.append({
                        "Nombre": name,
                        "Dirección": address,
                        "Teléfono": phone,
                        "Sitio Web": "Sin sitio web"
                    })
                    print(f"[{len(results)}] Encontrado: {name} (Sin sitio web)")
                else:
                    print(f"Saltado: {name} (Tiene sitio web)")

            except Exception as e:
                print(f"Error procesando '{name if 'name' in locals() else 'desconocido'}': {e}")
                continue

        await browser.close()
        return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python main.py 'tipo de negocio en ciudad'")
        sys.exit(1)
        
    query = sys.argv[1]
    data = asyncio.run(scrape_google_maps(query))
    
    if data:
        df = pd.DataFrame(data)
        df.to_csv("negocios_sin_web.csv", index=False, encoding='utf-8-sig')
        print(f"\nSe han guardado {len(data)} negocios sin sitio web en 'negocios_sin_web.csv'.")
    else:
        print("\nNo se encontraron negocios sin sitio web.")

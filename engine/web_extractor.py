import asyncio
import re
from playwright.async_api import Page, BrowserContext
from sources.base_source import Lead

# Regex para extracción
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
FB_REGEX = r'facebook\.com/[^/\s"]+'
IG_REGEX = r'instagram\.com/[^/\s"]+'
LI_REGEX = r'linkedin\.com/company/[^/\s"]+'

async def block_aggressively(route):
    """Bloquea imágenes, fuentes y estilos para máxima velocidad."""
    if route.request.resource_type in ["image", "font", "stylesheet", "media"]:
        await route.abort()
    else:
        await route.continue_()

async def extract_deep_data(lead: Lead, context: BrowserContext):
    """
    Visita la web del lead y extrae redes sociales, emails y píxeles.
    """
    if not lead.sitio_web or lead.sitio_web == "N/A":
        return lead

    page: Page = await context.new_page()
    # Aplicar bloqueo de recursos
    await page.route("**/*", block_aggressively)
    
    try:
        # Ir a la web con timeout corto y reintento silencioso en caso de redirecciones rápidas
        try:
            await page.goto(lead.sitio_web, wait_until="domcontentloaded", timeout=15000)
            # Espera extra progresiva para estabilización
            await asyncio.sleep(1.5)
        except Exception as e:
            if "ERR_NAME_NOT_RESOLVED" in str(e): return lead
            # Otros errores podrían permitir lectura parcial del DOM
        
        # Reintento de obtención de contenido para evitar error de navegación
        content = ""
        for _ in range(3):
            try:
                content = await page.content()
                if content: break
            except:
                await asyncio.sleep(1)
        
        if not content: return lead
        
        # 1. Extraer Emails
        emails = re.findall(EMAIL_REGEX, content)
        if emails:
            # Priorizar correos que no sean genéricos o simplemente el primero único
            lead.email = list(set(emails))[0]

        # 2. Redes Sociales
        fb = re.search(FB_REGEX, content)
        if fb: lead.facebook = f"https://{fb.group(0)}"
        
        ig = re.search(IG_REGEX, content)
        if ig: lead.instagram = f"https://{ig.group(0)}"
        
        li = re.search(LI_REGEX, content)
        if li: lead.linkedin_empresa = f"https://{li.group(0)}"

        # 3. Píxeles de Marketing
        if "connect.facebook.net" in content or "fbevents.js" in content:
            lead.pixel_fb = True
            
        if "googletagmanager.com" in content or "google-analytics.com" in content:
            lead.pixel_google = True

    except Exception as e:
        print(f"⚠️ Error escaneando web de {lead.nombre}: {e}")
    finally:
        await page.close()
    
    return lead

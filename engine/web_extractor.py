import asyncio
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse
from loguru import logger
from playwright.async_api import Page, BrowserContext
from sources.base_source import Lead

# Regex para extracción
EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
FB_REGEX = r'facebook\.com/[^/\s"]+'
IG_REGEX = r'instagram\.com/[^/\s"]+'
LI_REGEX = r'linkedin\.com/company/[^/\s"]+'
WA_REGEX = r'(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\+?\d+)'

def _public_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return not (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
            or ip.is_multicast or ip.is_unspecified
        )
    except ValueError:
        return False


async def _validated_public_url(value: str) -> str | None:
    try:
        parsed = urlparse(str(value).strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username or parsed.password:
            return None
        addresses = await asyncio.to_thread(
            socket.getaddrinfo, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        )
        if not addresses or any(not _public_ip(item[4][0]) for item in addresses):
            return None
        return parsed.geturl()
    except (OSError, ValueError):
        return None


async def block_aggressively(route, allowed_hosts=None):
    """Bloquea imágenes, fuentes, estilos y trackers para máxima velocidad."""
    resource_type = route.request.resource_type
    hostname = (urlparse(route.request.url).hostname or "").casefold()
    if allowed_hosts and hostname not in allowed_hosts:
        await route.abort()
        return

    # Bloqueos por tipo de recurso
    if resource_type in ["image", "font", "stylesheet", "media", "websocket", "other"]:
        await route.abort()
        return

    # Bloqueo de peticiones de red a rastreadores (ahorra muchísima RAM y CPU)
    # NOTA: Como bloqueamos a nivel de red, el texto "<script src=...>" sigue en el HTML
    # por lo tanto, nuestro detector de Píxeles más abajo SEGUIRÁ FUNCIONANDO.
    url = route.request.url.lower()
    trackers = ["google-analytics", "googletagmanager", "connect.facebook", "hotjar", "tiktok", "doubleclick"]
    if any(t in url for t in trackers):
        await route.abort()
        return

    await route.continue_()

async def extract_deep_data(lead: Lead, context: BrowserContext):
    """
    Visita la web del lead y extrae redes sociales, emails y píxeles.
    """
    if not lead.sitio_web or lead.sitio_web == "N/A":
        return lead

    safe_site = await _validated_public_url(lead.sitio_web)
    if not safe_site:
        logger.warning(f"URL no pública o inválida omitida para {lead.nombre}")
        return lead
    lead.sitio_web = safe_site
    host = (urlparse(safe_site).hostname or "").casefold()
    allowed_hosts = {host}
    alternate = host[4:] if host.startswith("www.") else f"www.{host}"
    alternate_url = safe_site.replace(host, alternate, 1)
    if await _validated_public_url(alternate_url):
        allowed_hosts.add(alternate)

    page: Page = await context.new_page()
    # Aplicar bloqueo de recursos
    await page.route("**/*", lambda route: block_aggressively(route, allowed_hosts))

    try:
        # Ir a la web con timeout corto
        try:
            await page.goto(lead.sitio_web, wait_until="domcontentloaded", timeout=8000)
            await asyncio.sleep(0.4)
        except Exception:
            pass # Intentar extraer contenido incluso si hay error de carga parcial

        content = await page.content()

        async def _extract_from_html(html):
            # 1. Extraer Emails
            found_emails = list(set(re.findall(EMAIL_REGEX, html)))

            # Priorizar enlaces semánticos reales (mailto:) inspirados en Crawl4AI / Autoscraper
            mailto_links = re.findall(r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})', html, re.IGNORECASE)
            if mailto_links:
                found_emails = list(set(mailto_links + found_emails))

            # Filtrar extensiones de imagen falsos positivos
            found_emails = [e for e in found_emails if not e.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'))]

            if found_emails:
                priority_patterns = ["gerencia", "direccion", "gerente", "comercial", "ventas", "ceo", "director", "administracion", "contacto", "info@"]
                best_email = found_emails[0]
                found_priority = False
                for pattern in priority_patterns:
                    for email in found_emails:
                        if pattern in email.lower():
                            best_email = email
                            found_priority = True
                            break
                    if found_priority: break
                return best_email
            return None

        email = await _extract_from_html(content)

        # SI NO HAY EMAIL: Buscar página de contacto
        if not email:
            contact_links = await page.query_selector_all("a")
            contact_url = None
            for link in contact_links:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href and any(x in href.lower() or x in text.lower() for x in ["contact", "nosotros", "legal", "quienes", "escribenos"]):
                    if href.startswith("/"):
                        contact_url = urljoin(lead.sitio_web, href)
                    elif href.startswith("http"):
                        contact_url = href
                    else:
                        contact_url = urljoin(lead.sitio_web, href)
                    break

            if contact_url:
                try:
                    contact_parsed = urlparse(contact_url)
                    if (contact_parsed.hostname or "").casefold() not in allowed_hosts:
                        raise ValueError("La URL de contacto sale del dominio corporativo")
                    if not await _validated_public_url(contact_url):
                        raise ValueError("La URL de contacto no es pública")
                    await page.goto(contact_url, wait_until="domcontentloaded", timeout=6000)
                    content_contact = await page.content()
                    email = await _extract_from_html(content_contact)
                except Exception:
                    pass

        if email:
            lead.email = email

        # 2. Redes Sociales y perfiles específicos
        # Buscar LinkedIn de personas/gerencia si es posible
        li_person = re.search(r'linkedin\.com/in/[^/\s"]+', content)
        if li_person:
            if not lead.notas: lead.notas = ""
            lead.notas = (lead.notas + f" [LinkedIn Personal: https://{li_person.group(0)}]").strip()
        # Descartar botones de compartir, plugins y rutas de Facebook/Instagram
        # que no son el perfil del negocio (primer match "limpio" gana).
        # El regex captura un solo segmento de ruta, así que comparamos exacto.
        _social_junk = {"sharer", "sharer.php", "share", "share.php", "plugins",
                        "dialog", "login", "l.php", "tr", "policies", "privacy",
                        "help", "intent", "p", "explore", "accounts", "hashtag",
                        "reel", "reels", "stories"}
        def _first_profile(pattern):
            for m in re.findall(pattern, content):
                segment = m.split("/", 1)[-1].split("?")[0].lower()
                if segment and segment not in _social_junk:
                    return f"https://{m}"
            return None

        fb = _first_profile(FB_REGEX)
        if fb: lead.facebook = fb

        ig = _first_profile(IG_REGEX)
        if ig: lead.instagram = ig

        li = re.search(LI_REGEX, content)
        if li: lead.linkedin_empresa = f"https://{li.group(0)}"

        # 3. Píxeles de Marketing
        if "connect.facebook.net" in content or "fbevents.js" in content:
            lead.pixel_fb = True

        if "googletagmanager.com" in content or "google-analytics.com" in content:
            lead.pixel_google = True

        # 4. Encontrar números de WhatsApp ocultos (¡Oro puro para ventas!)
        wa = re.search(WA_REGEX, content)
        if wa:
            wa_num = wa.group(1).strip()
            # Si Google Maps no nos dio número, o queremos priorizar el WhatsApp de la web:
            if not lead.telefono or lead.telefono == "N/A":
                lead.telefono = wa_num
            if not lead.notas: lead.notas = ""
            lead.notas = (lead.notas + f" [WA Web: {wa_num}]").strip()

        # 5. Extraer Meta Descripción (Como un resumen rápido de lo que hace la empresa)
        try:
            meta_desc_el = await page.query_selector("meta[name='description']")
            if meta_desc_el:
                meta_desc = await meta_desc_el.get_attribute("content")
                if meta_desc:
                    if not lead.notas: lead.notas = ""
                    lead.notas = (f"Info: {meta_desc[:150]}... | " + lead.notas).strip()
        except Exception:
            pass

        # 6. Señales de Software / Portales (Calificación)
        warm_signals = ["agendar cita", "reserva tu cita", "portal del paciente", "pago en línea", "pagos online", "doctoralia"]
        content_lower = content.lower()
        found_signals = [s for s in warm_signals if s in content_lower]
        if found_signals:
            if not lead.notas: lead.notas = ""
            lead.notas = (lead.notas + f" [Señales: {', '.join(found_signals)}]").strip()
            # Si tiene portal o citas, es un lead más maduro tecnológicamente
            if lead.calificacion == "frio":
                lead.calificacion = "bueno"

    except Exception as e:
        logger.warning(f"Error escaneando web de {lead.nombre}: {e}")
    finally:
        await page.close()

    return lead

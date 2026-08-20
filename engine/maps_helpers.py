"""Constantes y helpers de scraping para Google Maps.

Extraído del antiguo `scraper.py` monolítico. Solo contiene utilidades reutilizables
por las fuentes (`sources/google_maps.py`) y el orquestador.
"""
import asyncio
import re
import unicodedata
import urllib.parse

from loguru import logger

BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-blink-features=AutomationControlled',
    '--disable-features=IsolateOrigins,site-per-process',
    '--dns-prefetch-disable',
    '--no-first-run',
    '--window-size=1920,1080',
    '--disable-infobars',
    '--hide-scrollbars',
    '--mute-audio',
    '--ignore-certificate-errors',
]

_RATING_SELECTORS = [
    "div.F7nice span[aria-hidden='true']",
    "span.MW4etd",
    "span.ceNzKf[role='img']",
    "span[aria-label*='estrellas']", "span[aria-label*='stars']",
    "span[aria-label*='estrelas']",  "span[aria-label*='étoiles']",
    "span[aria-label*='Sterne']",
]
_REVIEW_SELECTORS = [
    "div.F7nice span[aria-label*='reseña']",
    "div.F7nice span[aria-label*='opinion']",
    "div.F7nice span[aria-label*='review']",
    "span.UY7F9",
    "span[aria-label*='opiniones']",
    "button[aria-label*='reseñas']",    "button[aria-label*='opiniones']",
    "button[aria-label*='reviews']",
    "button[aria-label*='avaliações']", "button[aria-label*='avis']",
    "button[aria-label*='Rezensionen']",
]
_WEB_SELECTORS = [
    "a[data-item-id='authority']",
    "a[aria-label*='Sitio web']",
    "a[data-value='Sitio web']",
    "a[data-item-id*='authority']",
]
_TYPE_SELECTORS = [
    'button[class*="Dener"]',
    'button[jsaction*="category"]',
    'button[class*="DkEaL"]',
]
_ADDRESS_SELECTORS = [
    "button[data-item-id='address']",
    "[data-item-id='address']",
    "button[aria-label^='Dirección:']",
    "button[aria-label^='Address:']",
]
_PHONE_SELECTORS = [
    "button[data-item-id^='phone:tel:']",
    "button[aria-label*='Llamar']",
    "button[aria-label*='Call']",
]
_PANEL_LOADED_SELECTORS = [
    "h1.DUwDvf", "h1[class*='DUwDvf']", "div[class*='fontHeadlineLarge']",
]
_NO_MORE_SELECTORS = [
    "span.HlvSq",
    "p.fontBodyMedium span",
    "div[class*='section-no-result']",
]

# Botón de consentimiento de cookies en distintos idiomas (Google decide según locale del navegador).
COOKIE_ACCEPT_TEXTS = [
    "Aceptar todo", "Aceptar", "Acepto",            # ES
    "Accept all", "I agree", "Accept",               # EN
    "Aceitar tudo", "Aceitar",                       # PT
    "Tout accepter", "J'accepte",                    # FR
    "Alle akzeptieren", "Akzeptieren",               # DE
]


def decode_google_url(url: str | None) -> str | None:
    """Decodifica una redireccion de Google a su URL destino real.

    Google envuelve los resultados de búsqueda en
    ``https://www.google.com/url?q=https%3A%2F%2Ftarget...``. Guardar esa
    envoltura en la DB rompe la deduplicacion (cada redireccion es unica) y
    deja enlaces rotos, asi que extraemos el destino real.
    """
    if not url:
        return url
    parsed = urllib.parse.urlparse(str(url).strip())
    if "google." not in (parsed.netloc or ""):
        return url
    if parsed.path not in ("", "/url"):
        return url
    target = urllib.parse.parse_qs(parsed.query).get("q")
    return target[0] if target else url


async def dorking_goto(page, url: str, timeout: int = 30000, retries: int = 3):
    """Navega a una búsqueda de Google con reintentos y backoff, cierra el
    consentimiento de cookies y detecta CAPTCHA/bloqueo.

    Retorna True si la página está lista para extraer; False si Google pidió
    captcha o consentimiento (en cuyo caso el caller debe abortar la fuente en
    vez de asumir que "no hay resultados").
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                await asyncio.sleep(1.5 * attempt)
    if last_error is not None:
        raise last_error

    await click_cookie_consent(page, timeout=2000)
    if await _is_captcha(page):
        logger.warning(f"CAPTCHA/consent de Google detectado para {str(url)[:80]}")
        return False
    return True


async def click_cookie_consent(page, timeout: int = 1000):
    """Cierra el consentimiento con un único timeout total, no uno por idioma."""
    selectors = ", ".join(
        f'button:has-text("{text.replace(chr(34), chr(92) + chr(34))}")'
        for text in COOKIE_ACCEPT_TEXTS
    )
    try:
        await page.locator(selectors).first.click(
            timeout=timeout,
            no_wait_after=True,
        )
        return True
    except Exception:
        return False


def _extract_place_id(url: str) -> str | None:
    """Extrae el CID de Google Maps (0xHEX:0xHEX) de la URL del lugar."""
    m = re.search(r'!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)', url or "")
    return m.group(1) if m else None


def _extract_place_coordinates(url: str) -> tuple[float | None, float | None]:
    """Extrae coordenadas exactas del lugar, nunca el centro del mapa (`@`)."""
    match = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", url or "")
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def _claim_place_for_scrape(
    url: str,
    known_place_ids: set[str] | None,
    seen_place_ids: set[str] | None,
) -> bool:
    """Reserva un lugar antes de abrirlo; los enlaces sin CID siguen siendo válidos."""
    place_id = _extract_place_id(url)
    if not place_id:
        return True
    if place_id in (known_place_ids or set()) or place_id in (seen_place_ids or set()):
        return False
    if seen_place_ids is not None:
        seen_place_ids.add(place_id)
    return True


def _parse_rating(*values: object) -> float | None:
    """Extrae una calificación decimal de texto visible o atributos ARIA."""
    for value in values:
        raw = str(value or "").strip()
        match = re.search(r"(?<!\d)([0-5](?:[.,]\d+)?)(?!\d)", raw)
        if not match:
            continue
        rating = float(match.group(1).replace(",", "."))
        if 0 <= rating <= 5:
            return rating
    return None


def _parse_review_count(*values: object) -> int | None:
    """Extrae reseñas soportando miles localizados y abreviaturas K/mil/M."""
    for value in values:
        raw = str(value or "").strip().casefold()
        if not raw:
            continue
        abbreviated = re.search(
            r"(\d+(?:[.,]\d+)?)\s*(k|mil|m|mill[oó]n(?:es)?)\b",
            raw,
        )
        if abbreviated:
            number = float(abbreviated.group(1).replace(",", "."))
            suffix = abbreviated.group(2)
            multiplier = 1_000 if suffix in {"k", "mil"} else 1_000_000
            return int(round(number * multiplier))

        match = re.search(r"\d[\d\s.,]*", raw)
        if match:
            digits = re.sub(r"\D", "", match.group(0))
            if digits:
                return int(digits)
    return None


def _extract_phone_candidate(
    data_item_id: object = None,
    aria_label: object = None,
    inner_text: object = None,
) -> str:
    """Prefiere el teléfono completo de `phone:tel:` y conserva el prefijo país."""
    item_id = str(data_item_id or "")
    if "phone:tel:" in item_id:
        candidate = item_id.split("phone:tel:", 1)[1].strip()
        if candidate:
            return candidate
    for value in (aria_label, inner_text):
        match = re.search(r"(\+?[\d\s().-]{7,})", str(value or ""))
        if match:
            return match.group(1).strip()
    return ""


def _norm_name(s: str) -> str:
    text = unicodedata.normalize("NFKD", str(s or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^\w]+", " ", text, flags=re.UNICODE).strip().casefold()


def _names_match(clicked_name: str, panel_name: str) -> bool:
    """Coincidencia de identidad; nunca acepta un nombre por mero prefijo."""
    def variants(value: str) -> set[str]:
        raw = str(value or "").strip()
        options = {_norm_name(raw)}
        # Maps puede añadir una categoría al aria-label: "Nombre · Categoría".
        if " · " in raw:
            options.add(_norm_name(raw.split(" · ", 1)[0]))
        return {option for option in options if option}

    return bool(variants(clicked_name) & variants(panel_name))


async def _wait_for_panel(page, name: str, timeout_ms: int = 6000, stop_check=lambda: False) -> bool:
    """Espera a que el panel cargado sea EL DEL NEGOCIO CLICKEADO (h1 == name).

    Google Maps es una SPA: al hacer click en el siguiente resultado, el panel
    del negocio ANTERIOR sigue en el DOM mientras carga el nuevo. Esperar a que
    exista "cualquier h1" hacía que teléfono/web/rating se leyeran del negocio
    equivocado. Retorna False si el panel correcto nunca aparece → el caller
    debe descartar el lead en vez de guardar datos cruzados.
    """
    deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
    while asyncio.get_event_loop().time() < deadline:
        if stop_check(): return False
        for sel in _PANEL_LOADED_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el:
                    txt = await el.inner_text()
                    if _names_match(name, txt):
                        return True
            except Exception:
                pass
        await asyncio.sleep(0.15)
    return False


async def _is_captcha(page) -> bool:
    url = page.url
    if any(x in url for x in ("sorry/index", "consent.google", "recaptcha")):
        return True
    el = await page.query_selector('iframe[src*="recaptcha"], #captcha, form#captcha-form')
    return el is not None


async def _scroll_and_wait(page, current_count: int, max_wait: float = 3.0, stop_check=lambda: False) -> int:
    feed = await page.query_selector("div[role='feed']")
    if not feed:
        return current_count
    await feed.evaluate("el => el.scrollBy(0, 1800)")
    t0 = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < max_wait:
        if stop_check(): break
        await asyncio.sleep(0.2)
        new_items = await page.query_selector_all("a.hfpxzc")
        if len(new_items) > current_count:
            return len(new_items)
    return current_count


async def _is_end_of_results(page, stop_check=lambda: False) -> bool:
    for sel in _NO_MORE_SELECTORS:
        if stop_check(): break
        try:
            el = await page.query_selector(sel)
            if el:
                txt = (await el.inner_text()).lower()
                if any(k in txt for k in ("todos los result", "no result", "no hay result",
                                           "no se encontr", "no more", "end of result")):
                    return True
        except Exception:
            pass
    return False

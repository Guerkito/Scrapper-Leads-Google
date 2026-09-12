"""Genera la oferta y el cliente ideal (ICP) a partir de la web del usuario.

Reutiliza el LLM local (Ollama) que ya usan el expansor de búsquedas y el bot
de WhatsApp. No depende de APIs externas ni de claves.
"""

from __future__ import annotations

import json
import re

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import OLLAMA_CHAT_URL, OLLAMA_MODEL


MAX_SITE_CHARS = 4000
MAX_SEGMENTS = 4
MAX_QUERIES = 6
MAX_ROLES = 6


ICP_PROMPT = """Eres un estratega de ventas B2B. Analiza la web de esta empresa y \
define su oferta y su cliente ideal.

Devuelve SOLO un JSON con esta forma exacta:
{
  "negocio": "qué vende, en una frase",
  "pitch": "propuesta de valor en una frase orientada al cliente",
  "roles_decision": ["3 a 5 cargos a los que contactar"],
  "dolores": ["2 a 4 problemas que resuelve su oferta"],
  "segmentos": [
    {"label": "tipo de cliente", "queries": ["3 a 5 búsquedas de Google Maps para encontrarlo"]}
  ]
}

Reglas:
- Genera entre 2 y 4 segmentos; ordena del cliente más afín al menos afín.
- Las queries deben ser términos reales de negocios en español, usables en \
Google Maps, sin nombres de ciudades ni países.
- No inventes servicios que la web no mencione.

WEB DE LA EMPRESA:
"""


def _normalizar_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def fetch_site_text(url: str, timeout: int = 12) -> str:
    """Descarga y limpia el texto visible de una web. Devuelve '' si falla."""
    target = _normalizar_url(url)
    if not target:
        return ""
    try:
        response = requests.get(
            target,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OnyxICP/1.0)"},
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning(f"ICP: no se pudo leer {target} ({exc})")
        return ""
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    return text[:MAX_SITE_CHARS]


def parse_icp(content: str) -> dict:
    """Valida y normaliza el JSON devuelto por el LLM."""
    raw = (content or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("El asistente no devolvió un JSON válido.") from exc
    if not isinstance(data, dict):
        raise ValueError("El asistente no devolvió un objeto JSON.")

    def _text(value, limit):
        return str(value or "").strip()[:limit]

    def _list(value, limit):
        if not isinstance(value, list):
            return []
        return [str(item).strip()[:200] for item in value if str(item or "").strip()][:limit]

    segments = []
    for item in data.get("segmentos") or []:
        if not isinstance(item, dict):
            continue
        label = _text(item.get("label"), 80)
        queries = _list(item.get("queries"), MAX_QUERIES)
        if label and queries:
            segments.append({"label": label, "queries": queries})
        if len(segments) >= MAX_SEGMENTS:
            break
    if not segments:
        raise ValueError("El asistente no generó tipos de cliente. Prueba de nuevo.")

    negocio = _text(data.get("negocio"), 200)
    pitch = _text(data.get("pitch"), 300)
    if not negocio or not pitch:
        raise ValueError("El asistente no describió la oferta. Prueba de nuevo.")

    return {
        "negocio": negocio,
        "pitch": pitch,
        "roles_decision": _list(data.get("roles_decision"), MAX_ROLES) or ["Gerencia"],
        "dolores": _list(data.get("dolores"), 4),
        "segmentos": segments,
    }


def build_icp(url: str) -> dict:
    """Lee la web del usuario y devuelve su ICP validado.

    Lanza ValueError con un mensaje en español cuando no se puede completar.
    """
    text = fetch_site_text(url)
    if not text:
        raise ValueError("No se pudo leer la web. Revisa la URL e intenta de nuevo.")

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [{"role": "user", "content": ICP_PROMPT + text}],
    }
    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=120)
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "")
        return parse_icp(content)
    except ValueError:
        raise
    except Exception as exc:
        logger.error(f"ICP: fallo el asistente local ({exc})")
        raise ValueError(
            "El asistente local (Ollama) no está disponible. Arráncalo e intenta de nuevo."
        ) from exc

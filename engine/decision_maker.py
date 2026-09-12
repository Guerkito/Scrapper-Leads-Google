"""Extrae el decisor real (nombre, cargo, LinkedIn) desde la web del lead.

Solo guarda lo que aparece en la web: si no hay evidencia, deja los campos vacíos.
Usa el LLM local (Ollama), igual que el resto del sistema.
"""

from __future__ import annotations

import json
import re

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import OLLAMA_CHAT_URL, OLLAMA_MODEL
from db import open_conn
from engine.icp_builder import _normalizar_url


MAX_TEXTO = 6000
LINKEDIN_IN_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+", re.IGNORECASE
)

PROMPT = """Analiza la web de esta empresa y extrae a su decisor \
(dueño, fundador, gerente o director).

Devuelve SOLO JSON con esta forma exacta:
{"nombre": "nombre completo de la persona o null", "cargo": "cargo o null", \
"linkedin": "URL de linkedin.com/in/... o null"}

Reglas:
- Usa únicamente información que aparezca en la web; no inventes nada.
- Si no hay una persona identificable, devuelve null en los tres campos.
- El LinkedIn solo puede ser una de las URLs de la lista de enlaces detectados.

Enlaces de LinkedIn detectados:
{links}

WEB:
{texto}
"""


def _slug(url: str) -> str:
    match = LINKEDIN_IN_RE.search(url or "")
    if not match:
        return ""
    return match.group(0).rstrip("/").rsplit("/", 1)[-1].casefold()


def _fetch_site(url: str, timeout: int = 12) -> tuple[str, list[str]]:
    """Devuelve (texto visible, enlaces LinkedIn de la página). Vacío si falla."""
    target = _normalizar_url(url)
    if not target:
        return "", []
    try:
        response = requests.get(
            target,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OnyxDecisor/1.0)"},
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning(f"Decisor: no se pudo leer {target} ({exc})")
        return "", []
    soup = BeautifulSoup(response.text, "html.parser")
    links = list(dict.fromkeys(LINKEDIN_IN_RE.findall(str(soup))))
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    texto = re.sub(r"\s+", " ", soup.get_text(" ")).strip()[:MAX_TEXTO]
    return texto, links


def parse_decision(content: str, linkedin_links: list[str] | None = None) -> dict:
    """Valida y normaliza el JSON del LLM. Sin nombre no hay decisor."""
    raw = (content or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"nombre": None, "cargo": None, "linkedin": None}
    if not isinstance(data, dict):
        return {"nombre": None, "cargo": None, "linkedin": None}

    def _limpio(value, limit=120):
        text = str(value or "").strip()
        if text.casefold() in {"", "null", "none", "n/a"}:
            return None
        return text[:limit]

    nombre = _limpio(data.get("nombre"))
    if not nombre:
        return {"nombre": None, "cargo": None, "linkedin": None}
    cargo = _limpio(data.get("cargo"))
    linkedin = None
    candidate = _limpio(data.get("linkedin"), 300)
    if candidate:
        slug = _slug(candidate)
        valid_slugs = {_slug(url) for url in (linkedin_links or [])}
        if slug and slug in valid_slugs:
            linkedin = candidate
    return {"nombre": nombre, "cargo": cargo, "linkedin": linkedin}


def _ask_llm(texto: str, links: list[str]) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "user",
                "content": PROMPT.format(links="\n".join(links) or "(ninguno)", texto=texto),
            }
        ],
    }
    response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=120)
    response.raise_for_status()
    content = response.json().get("message", {}).get("content", "")
    return parse_decision(content, links)


def enrich_lead(lead: dict) -> dict | None:
    """Lee la web del lead y devuelve su decisor, o None si no hay evidencia."""
    texto, links = _fetch_site(lead.get("sitio_web") or "")
    if not texto:
        return None
    decision = _ask_llm(texto, links)
    if not decision.get("nombre"):
        return None
    return decision


def save_decision(lead_id: int, decision: dict) -> None:
    with open_conn() as conn:
        conn.execute(
            "UPDATE leads SET decisor_nombre = ?, decisor_cargo = ?, decisor_linkedin = ? "
            "WHERE id = ?",
            (
                decision.get("nombre"),
                decision.get("cargo"),
                decision.get("linkedin"),
                lead_id,
            ),
        )


def pending_count() -> int:
    with open_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM leads
            WHERE COALESCE(sitio_web, '') NOT IN ('', 'N/A', 'sin sitio web')
              AND COALESCE(decisor_nombre, '') = ''
              AND COALESCE(estado, '') != 'Descartado'
            """
        ).fetchone()
    return int(row[0] or 0)


def enrich_batch(limit: int = 20, on_progress=None) -> int:
    """Enriquece hasta `limit` leads con web y sin decisor. Devuelve cuántos guardó."""
    with open_conn() as conn:
        conn.row_factory = None
        rows = conn.execute(
            """
            SELECT id, nombre, sitio_web FROM leads
            WHERE COALESCE(sitio_web, '') NOT IN ('', 'N/A', 'sin sitio web')
              AND COALESCE(decisor_nombre, '') = ''
              AND COALESCE(estado, '') != 'Descartado'
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    saved = 0
    for index, (lead_id, nombre, sitio_web) in enumerate(rows, start=1):
        if on_progress:
            on_progress(index, len(rows), nombre)
        try:
            decision = enrich_lead({"sitio_web": sitio_web})
            if decision:
                save_decision(lead_id, decision)
                saved += 1
                logger.info(f"Decisor guardado para {nombre}: {decision['nombre']}")
        except Exception as exc:
            logger.warning(f"Decisor: fallo con {nombre} ({exc})")
    return saved

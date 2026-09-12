"""Catalogo local de nichos para evitar bloquear la busqueda esperando al LLM."""

from __future__ import annotations

import re
import unicodedata

from nichos_dict import NICHOS
from services.constants import NICHO_SYNONYMS, NICHOS_DICT


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def resolve_niche(value: str) -> dict | None:
    """Resuelve consultas, sector y tipo para cualquier opcion visible en la UI."""
    wanted = normalize_text(value)
    if not wanted:
        return None

    for key, data in NICHOS.items():
        if wanted in {normalize_text(key), normalize_text(key.replace("_", " "))}:
            return {
                "queries": list(data.get("queries_maps", [])),
                "sector": data.get("sector", "General"),
                "tipo": data.get("tipo", "B2B"),
            }

    for sector, niches in NICHOS_DICT.items():
        for niche in niches:
            synonyms = NICHO_SYNONYMS.get(niche, [])
            if wanted in {normalize_text(item) for item in [niche, *synonyms]}:
                queries = list(dict.fromkeys([niche, *synonyms]))
                is_b2c = any(
                    token in normalize_text(sector)
                    for token in (
                        "salud", "gastronomia", "belleza", "mascotas", "eventos",
                        "moda", "retail", "deportes", "turismo", "hogar", "ocio",
                    )
                )
                return {
                    "queries": queries,
                    "sector": sector.title(),
                    "tipo": "B2C" if is_b2c else "B2B",
                }
    return None

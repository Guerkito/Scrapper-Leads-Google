import json
import asyncio
import httpx
from loguru import logger
from config import OLLAMA_CHAT_URL, OLLAMA_MODEL
from engine.niche_catalog import resolve_niche

async def _expand_single_term(t: str, client: httpx.AsyncClient) -> list[str]:
    """Expande un solo término usando el diccionario o IA."""
    local = resolve_niche(t)
    if local:
        return local["queries"]

    # 2. Consultar a Ollama en paralelo si no está en el dict
    prompt = f"""Eres un experto en búsquedas de Google Maps en Colombia. 
Dado el término "{t}", genera exactamente 5 variaciones de búsqueda 
que una persona usaría en Google Maps para encontrar ese tipo de negocio.
Responde SOLO con una lista JSON de strings. Sin explicaciones.
Usa términos en español colombiano."""

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json"
    }

    try:
        response = await client.post(OLLAMA_CHAT_URL, json=payload, timeout=5.0)
        if response.status_code == 200:
            content = response.json().get("message", {}).get("content", "[]")
            vars_ia = json.loads(content)
            if isinstance(vars_ia, list) and len(vars_ia) > 0:
                return vars_ia
    except Exception as exc:
        logger.debug(f"Expansor local/LLM: usando termino directo ({exc})")
    
    return [t]

async def expandir_query(query_input: str) -> list[str]:
    """
    Expande términos de búsqueda de forma asíncrona y paralela.
    """
    if not query_input:
        return []
        
    terminos = [t.strip() for t in query_input.split(",") if t.strip()]
    
    # Si hay demasiados términos (>15), limitamos la expansión IA para evitar lentitud extrema
    if len(terminos) > 15:
        logger.info(f"Demasiados términos ({len(terminos)}). Usando términos directos para optimizar.")
        return list(dict.fromkeys(terminos))

    async with httpx.AsyncClient() as client:
        tareas = [_expand_single_term(t, client) for t in terminos]
        resultados = await asyncio.gather(*tareas)
        
    # Aplanar y deduplicar
    todas_variaciones = [item for sublist in resultados for item in sublist]
    return list(dict.fromkeys(todas_variaciones))

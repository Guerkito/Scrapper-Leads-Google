import asyncio
import random
from typing import List
from loguru import logger
from config import MAX_CONCURRENT
from sources.base_source import BaseSource, Lead
from engine.query_expander import expandir_query
from engine.web_extractor import extract_deep_data
from db import open_conn, save_lead, init_db, load_known_identifiers
from services.phone_utils import phone_digits
from services.product_campaigns import apply_campaign_context

from playwright.async_api import async_playwright
from engine.maps_helpers import BROWSER_ARGS

from engine.niche_catalog import resolve_niche
from geo_data import GEO_DATA

def _lead_has_website(lead: Lead) -> bool:
    site = (lead.sitio_web or "").strip()
    if site.casefold() not in {"", "n/a", "nan", "none", "null", "sin sitio web"}:
        return True
    return bool(lead.tiene_web)

def _lead_matches_hunter_mode(lead: Lead) -> bool:
    return not _lead_has_website(lead)


def _known_phone_ids(conn) -> set[str]:
    """Identidades de teléfono existentes; evita reconstruir una cola repetida."""
    rows = conn.execute(
        "SELECT telefono_e164, telefono, pais FROM leads "
        "WHERE telefono_e164 IS NOT NULL OR telefono IS NOT NULL"
    ).fetchall()
    return {
        digits
        for e164, raw, country in rows
        if (digits := phone_digits(e164 or raw, country))
    }

class Orchestrator:
    def __init__(self, fuentes: List[BaseSource], log_callback=None, lead_callback=None):
        self.fuentes = fuentes
        self.log_callback = log_callback
        self.lead_callback = lead_callback
        self.stop_requested = False
        self.callable_phones_found = 0

        # Reducimos concurrencia para evitar CAPTCHAs masivos
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        init_db()

    def stop(self):
        """Solicita la detención de la misión."""
        self.stop_requested = True
        self._log("Solicitud de parada recibida. Abortando misión...")

    def _log(self, msg):
        logger.info(msg)
        if self.log_callback:
            self.log_callback(msg)

    def _existing_lead_has_website(self, lead: Lead) -> bool:
        try:
            with open_conn() as conn:
                row = conn.execute(
                    """
                    SELECT sitio_web, tiene_web FROM leads
                    WHERE lower(trim(nombre)) = lower(trim(?))
                      AND lower(trim(COALESCE(ciudad, ''))) = lower(trim(?))
                      AND lower(trim(COALESCE(pais, ''))) = lower(trim(?))
                    LIMIT 1
                    """,
                    (lead.nombre, lead.ciudad, getattr(lead, "pais", "")),
                ).fetchone()
            if not row:
                return False
            site = (row[0] or "").strip()
            return bool(
                site.casefold() not in {"", "n/a", "nan", "none", "null", "sin sitio web"}
                or row[1]
            )
        except Exception:
            return False

    async def buscar_fuente(
        self, fuente: BaseSource, queries: List[str], punto: str, location: dict,
        context, limit: int = 20, hunter_mode: bool = False, nicho_original: str = "",
        cold_call_mode: bool = False, known_place_ids: set[str] | None = None,
        seen_place_ids: set[str] | None = None,
        known_phone_ids: set[str] | None = None,
        callable_phone_ids: set[str] | None = None,
        product_campaign: str = "busqueda_libre",
        target_segments: list[str] | None = None,
    ) -> List[Lead]:
        """Lanza búsqueda para una fuente con manejo de errores y múltiples queries."""
        ciudad_nombre = location["ciudad"]
        metadata = resolve_niche(nicho_original) or {}
        query_candidates = list(queries)
        usable_queries = (
            query_candidates
            if cold_call_mode
            else query_candidates[:max(1, int(limit))]
        )
        if not usable_queries:
            return []
        base, remainder = divmod(max(1, int(limit)), len(usable_queries))
        known_phone_ids = known_phone_ids if known_phone_ids is not None else set()
        callable_phone_ids = callable_phone_ids if callable_phone_ids is not None else set()

        def prepare_lead(lead_obj, query_metadata=None, source_query=""):
            effective_metadata = query_metadata or metadata
            lead_obj.ciudad = ciudad_nombre
            lead_obj.pais = location.get("pais") or getattr(lead_obj, "pais", None)
            lead_obj.departamento = location.get("departamento") or getattr(lead_obj, "departamento", None)
            lead_obj.zona = location.get("zona") or getattr(lead_obj, "zona", None)
            lead_obj.sector = effective_metadata.get("sector", lead_obj.sector)
            lead_obj.tipo = effective_metadata.get("tipo", lead_obj.tipo)
            lead_obj.calificacion = fuente.calificar(lead_obj)
            apply_campaign_context(
                lead_obj, product_campaign, target_segments, source_query
            )
            return lead_obj

        async def run_query(index, query, requested_limit=None):
            if self.stop_requested:
                return []
            query_limit = (
                requested_limit
                if requested_limit is not None
                else base + (1 if index < remainder else 0)
            )
            query_metadata = resolve_niche(query) or metadata
            async with self.semaphore:
                if self.stop_requested:
                    return []

                await asyncio.sleep(random.uniform(0.25, 0.8))

                try:
                    self._log(f"[{fuente.__class__.__name__}] Buscando: {query} en {ciudad_nombre}...")

                    def _on_lead_captured(lead_obj):
                        if self.stop_requested:
                            return
                        try:
                            prepare_lead(lead_obj, query_metadata, query)

                            phone_id = ""
                            if cold_call_mode:
                                if len(callable_phone_ids) >= limit:
                                    return False
                                phone_id = phone_digits(
                                    getattr(lead_obj, "telefono_e164", None)
                                    or getattr(lead_obj, "telefono", None),
                                    getattr(lead_obj, "pais", None),
                                )
                                if (
                                    not phone_id
                                    or phone_id in known_phone_ids
                                    or phone_id in callable_phone_ids
                                ):
                                    return False

                            if hunter_mode and (
                                not _lead_matches_hunter_mode(lead_obj)
                                or self._existing_lead_has_website(lead_obj)
                            ):
                                self._log(f"⏭️ Omitido hunter: {lead_obj.nombre[:45]}")
                                return

                            with open_conn() as conn:
                                status = save_lead(lead_obj, conn)
                            if status >= 0 and cold_call_mode:
                                callable_phone_ids.add(phone_id)
                                self.callable_phones_found += 1
                            if status >= 0 and self.lead_callback:
                                self.lead_callback(lead_obj, status == 1)
                            return status >= 0
                        except Exception as e:
                            self._log(f"Error guardando lead: {e}")
                            return False

                    leads = await fuente.buscar(
                        query=query,
                        ciudad=punto,
                        context=context,
                        limit=query_limit,
                        lead_callback=_on_lead_captured,
                        stop_check=lambda: self.stop_requested or (
                            cold_call_mode and len(callable_phone_ids) >= limit
                        ),
                        hunter_mode=hunter_mode,
                        known_place_ids=known_place_ids,
                        seen_place_ids=seen_place_ids,
                    )
                    if self.stop_requested:
                        return []

                    for l in leads:
                        prepare_lead(l, query_metadata, query)

                    if hunter_mode:
                        leads = [
                            l for l in leads
                            if _lead_matches_hunter_mode(l)
                            and not self._existing_lead_has_website(l)
                        ]

                    if cold_call_mode:
                        leads = [
                            lead for lead in leads
                            if phone_digits(
                                getattr(lead, "telefono_e164", None)
                                or getattr(lead, "telefono", None),
                                getattr(lead, "pais", None),
                            ) in callable_phone_ids
                        ]

                    return leads
                except Exception as e:
                    if not self.stop_requested:
                        self._log(f"Error en fuente {fuente.__class__.__name__} con query '{query}': {e}")
                    return []

        if cold_call_mode:
            batches = []
            for index, query in enumerate(usable_queries):
                remaining = max(0, int(limit) - len(callable_phone_ids))
                if self.stop_requested or remaining == 0:
                    break
                batches.append(await run_query(index, query, requested_limit=remaining))
        else:
            batches = await asyncio.gather(
                *(run_query(i, query) for i, query in enumerate(usable_queries)),
                return_exceptions=False,
            )
        return [lead for batch in batches for lead in batch][:limit]

    async def buscar_todos(
        self, nicho_input: str, ciudades: List[str | dict], deep_scan: bool = False,
        limit: int = 20, hunter_mode: bool = False, pais: str = "",
        cold_call_mode: bool = False, _shared_context=None,
        product_campaign: str = "busqueda_libre",
        target_segments: list[str] | None = None,
        query_override: list[str] | None = None,
    ) -> List[Lead]:
        """
        Coordina el proceso completo para múltiples ciudades y modo Deep Scan.
        """
        if self.stop_requested: return []
        self._log(f"Preparando inteligencia de búsqueda para: {nicho_input}")
        queries = (
            list(dict.fromkeys(query_override))
            if query_override
            else await expandir_query(nicho_input)
        )
        if self.stop_requested: return []

        # En modo llamada la primera consulta es la canónica y solo se expande si falta cuota.
        if not cold_call_mode:
            random.shuffle(queries)

        if hunter_mode:
            self._log("MODO HUNTER ACTIVADO: Google Maps, negocios sin sitio web.")
        if cold_call_mode:
            self._log(
                f"LISTA PARA LLAMAR: objetivo de {limit} teléfonos nuevos, válidos y únicos por ciudad."
            )

        self._log(f"Iniciando misión multi-ciudad. Variaciones de búsqueda: {len(queries)}")

        async def collect(context):
            collected = []
            for location_value in ciudades:
                if self.stop_requested:
                    break
                location = (
                    dict(location_value)
                    if isinstance(location_value, dict)
                    else {"ciudad": str(location_value), "pais": pais}
                )
                location.setdefault("pais", pais)
                ciudad = location["ciudad"]
                with open_conn() as known_conn:
                    _, known_place_ids = load_known_identifiers(ciudad, known_conn)
                    known_phone_ids = _known_phone_ids(known_conn)
                seen_place_ids: set[str] = set()
                callable_phone_ids: set[str] = set()

                qualified_location = ", ".join(filter(None, [
                    ciudad, location.get("departamento"), location.get("pais")
                ]))
                puntos_gps = [qualified_location]
                if deep_scan:
                    from city_coords import generate_grid, CITY_COORDS
                    countries = {
                        country
                        for country, regions in GEO_DATA.items()
                        if any(ciudad in names for names in regions.values())
                    }
                    if len(countries) > 1:
                        self._log(
                            f"[DEEP SCAN] {ciudad} es ambigua entre países; "
                            "se usa búsqueda textual para evitar coordenadas incorrectas."
                        )
                    elif ciudad in CITY_COORDS:
                        grid = generate_grid(ciudad, grid_n=3)
                        if grid:
                            puntos_gps = grid
                            self._log(f"[DEEP SCAN] Generados {len(grid)} puntos GPS para {ciudad}")

                for punto in puntos_gps:
                    if self.stop_requested or (
                        cold_call_mode and len(callable_phone_ids) >= limit
                    ):
                        break
                    source_batches = await asyncio.gather(*(
                        self.buscar_fuente(
                            source, queries, punto, location, context,
                            limit=limit, hunter_mode=hunter_mode,
                            nicho_original=nicho_input,
                            cold_call_mode=cold_call_mode,
                            known_place_ids=known_place_ids,
                            seen_place_ids=seen_place_ids,
                            known_phone_ids=known_phone_ids,
                            callable_phone_ids=callable_phone_ids,
                            product_campaign=product_campaign,
                            target_segments=target_segments,
                        )
                        for source in self.fuentes
                    ))
                    collected.extend(lead for batch in source_batches for lead in batch)
            return collected

        if _shared_context is not None:
            todos_los_leads_brutos = await collect(_shared_context)
        else:
            async with async_playwright() as p:
                if self.stop_requested:
                    return []
                browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
                try:
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                    )
                    todos_los_leads_brutos = await collect(context)
                finally:
                    await browser.close()

        if self.stop_requested:
            self._log("Misión abortada con éxito.")
            return []

        # Enriquecimiento (Deep Scraping) en Paralelo
        raw_results = todos_los_leads_brutos
        unique_results = {}
        for lead in todos_los_leads_brutos:
            identity = (
                getattr(lead, "maps_url", None)
                or getattr(lead, "perfil_url", None)
                or (
                    str(lead.nombre).strip().casefold(),
                    str(lead.ciudad).strip().casefold(),
                    str(getattr(lead, "pais", "") or "").strip().casefold(),
                )
            )
            unique_results.setdefault(str(identity), lead)
        todos_los_leads_brutos = list(unique_results.values())

        enrichment_by_site = {}
        if not hunter_mode and not cold_call_mode:
            for lead in todos_los_leads_brutos:
                if lead.tiene_web and lead.sitio_web:
                    enrichment_by_site.setdefault(lead.sitio_web.strip().casefold(), lead)
        leads_a_enriquecer = list(enrichment_by_site.values())

        if leads_a_enriquecer and not self.stop_requested:
            self._log(f"🔎 Iniciando extracción profunda de emails para {len(leads_a_enriquecer)} leads...")
            async def enrich(context):
                async def enrich_task(lead):
                    if self.stop_requested:
                        return
                    async with self.semaphore:
                        lead_enriquecido = await extract_deep_data(lead, context)
                        with open_conn() as conn:
                            save_lead(lead_enriquecido, conn)
                        if self.lead_callback:
                            # None = enriquecimiento: no cuenta como nuevo ni duplicado.
                            self.lead_callback(lead_enriquecido, None)
                await asyncio.gather(*(enrich_task(lead) for lead in leads_a_enriquecer))

            if _shared_context is not None:
                await enrich(_shared_context)
            else:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
                    try:
                        context = await browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                            ignore_https_errors=True
                        )
                        await enrich(context)
                    finally:
                        await browser.close()

        self._log(f"Misión completada.")
        return raw_results

    async def buscar_lote(
        self, nichos: List[str], ciudades: List[str | dict], deep_scan=False,
        limit=20, hunter_mode=False, pais="", cold_call_mode=False,
        product_campaign="busqueda_libre", target_segments=None,
    ) -> List[Lead]:
        """Ejecuta un barrido completo reutilizando un solo Chromium."""
        all_results = []
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, args=BROWSER_ARGS)
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    ignore_https_errors=True,
                )
                for niche in nichos:
                    if self.stop_requested:
                        break
                    self._log(f"Procesando nicho: {niche}")
                    results = await self.buscar_todos(
                        niche, ciudades, deep_scan=deep_scan, limit=limit,
                        hunter_mode=hunter_mode, pais=pais,
                        cold_call_mode=cold_call_mode, _shared_context=context,
                        product_campaign=product_campaign,
                        target_segments=target_segments,
                    )
                    all_results.extend(results)
            finally:
                await browser.close()
        return all_results

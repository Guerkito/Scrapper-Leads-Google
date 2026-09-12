import asyncio
import threading
import random
import datetime
import uuid
from engine.orchestrator import Orchestrator
from services.constants import NICHOS_DICT
from services.leads import invalidate_leads_cache
from services.product_campaigns import FREE_CAMPAIGN, build_search_terms, campaign_label
from db import open_conn, save_search_history

class SearchMission:
    def __init__(self):
        self._lock = threading.RLock()
        self.running = False
        self.orchestrator = None
        self.total_processed = 0
        self._thread = None
        self.last_error = None
        self.total_duplicates = 0
        self.last_summary = None
        self.cold_call_mode = False
        self.product_campaign = FREE_CAMPAIGN
        self.target_segments = []
        self.logs = []

    def add_log(self, message):
        """Guarda logs sin depender del contexto interno de Streamlit."""
        entry = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}"
        with self._lock:
            self.logs.append(entry)
            if len(self.logs) > 200:
                del self.logs[:-200]

    def snapshot(self):
        """Devuelve una fotografía consistente para el fragmento de la UI."""
        with self._lock:
            return {
                "running": self.running,
                "total_processed": self.total_processed,
                "total_duplicates": self.total_duplicates,
                "last_error": self.last_error,
                "last_summary": dict(self.last_summary) if self.last_summary else None,
                "cold_call_mode": self.cold_call_mode,
                "product_campaign": self.product_campaign,
                "target_segments": list(self.target_segments),
                "callable_phones_found": getattr(
                    self.orchestrator, "callable_phones_found", 0
                ),
                "logs": list(self.logs),
            }

    def start(
        self, sources, callback, nicho, ciudades, deep, limit, is_barrido,
        hunter_mode=False, pais="", cold_call_mode=False,
        product_campaign=FREE_CAMPAIGN, target_segments=None,
    ):
        def count_cb(n, is_new=True):
            with self._lock:
                if is_new is None:
                    # Enriquecimiento/actualización de un lead ya guardado:
                    # no es ni nuevo ni duplicado.
                    return
                # Solo incrementamos si es un lead realmente nuevo.
                if is_new:
                    increment = 1 if not isinstance(n, int) else n
                    self.total_processed += increment
                else:
                    self.total_duplicates += 1

        def log_cb(message):
            self.add_log(message)
            if callback:
                try:
                    callback(message)
                except Exception:
                    # Los callbacks externos son opcionales; el log interno siempre queda.
                    pass

        with self._lock:
            if self.running:
                return False
            self.mision_id = uuid.uuid4().hex[:12]
            self.orchestrator = Orchestrator(
                sources, log_callback=log_cb, lead_callback=count_cb
            )
            self.orchestrator.mision_id = self.mision_id
            self.running = True
            self.total_processed = 0
            self.total_duplicates = 0
            self.last_error = None
            self.last_summary = None
            self.cold_call_mode = cold_call_mode
            self.product_campaign = product_campaign or FREE_CAMPAIGN
            self.target_segments = list(target_segments or [])
            self.logs = []
        campaign_queries = build_search_terms(product_campaign, target_segments)
        if product_campaign != FREE_CAMPAIGN:
            self.add_log(
                f"Campaña {campaign_label(product_campaign)}: "
                f"{len(campaign_queries)} términos específicos."
            )
        if cold_call_mode:
            self.add_log(
                "Lista para llamar: buscando teléfonos válidos y únicos "
                "sin enriquecimiento web profundo."
            )
        elif hunter_mode:
            self.add_log(
                "Modo hunter: usando Google Maps y capturando negocios sin sitio web."
            )

        def _target():
            loop = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                if is_barrido or "BARRIDO TOTAL" in nicho.upper() or "TODAS LAS EMPRESAS" in nicho.upper():
                    todos_los_nichos = []
                    for sector, sub_nichos in NICHOS_DICT.items():
                        if "TODO EL MERCADO" in sector: continue
                        # Limpiar etiquetas de "TODOS LOS SUBNICHOS"
                        nichos_limpios = [n for n in sub_nichos if "TODOS LOS SUBNICHOS" not in n]
                        todos_los_nichos.extend(nichos_limpios)

                    random.shuffle(todos_los_nichos)
                    self.orchestrator._log(f"BARRIDO TOTAL ACTIVADO. Escaneando {len(todos_los_nichos)} nichos en orden aleatorio...")
                    loop.run_until_complete(self.orchestrator.buscar_lote(
                        todos_los_nichos, ciudades, deep_scan=deep, limit=limit,
                        hunter_mode=hunter_mode, pais=pais,
                        cold_call_mode=cold_call_mode,
                        product_campaign=product_campaign,
                        target_segments=target_segments,
                    ))

                elif "TODOS LOS SUBNICHOS" in nicho.upper():
                    # Buscar a qué sector pertenece este "TODOS LOS SUBNICHOS"
                    nichos_sector = []
                    for s_name, s_list in NICHOS_DICT.items():
                        if nicho in s_list:
                            nichos_sector = [n for n in s_list if "TODOS LOS SUBNICHOS" not in n]
                            break

                    if nichos_sector:
                        random.shuffle(nichos_sector)
                        self.orchestrator._log(f"BARRIDO DE SECTOR ACTIVADO. Escaneando {len(nichos_sector)} sub-nichos en orden aleatorio...")
                        loop.run_until_complete(self.orchestrator.buscar_lote(
                            nichos_sector, ciudades, deep_scan=deep, limit=limit,
                            hunter_mode=hunter_mode, pais=pais,
                            cold_call_mode=cold_call_mode,
                            product_campaign=product_campaign,
                            target_segments=target_segments,
                        ))
                    else:
                        self.orchestrator._log(f"Objetivo: '{nicho}'")
                        loop.run_until_complete(self.orchestrator.buscar_todos(
                            nicho, ciudades, deep_scan=deep, limit=limit,
                            hunter_mode=hunter_mode, pais=pais,
                            cold_call_mode=cold_call_mode,
                            product_campaign=product_campaign,
                            target_segments=target_segments,
                            query_override=campaign_queries,
                        ))
                else:
                    self.orchestrator._log(f"Objetivo: '{nicho}'")
                    loop.run_until_complete(self.orchestrator.buscar_todos(
                        nicho, ciudades, deep_scan=deep, limit=limit,
                        hunter_mode=hunter_mode, pais=pais,
                        cold_call_mode=cold_call_mode,
                        product_campaign=product_campaign,
                        target_segments=target_segments,
                        query_override=campaign_queries,
                    ))

                self.orchestrator._log(f"Misión finalizada con éxito.")
            except Exception as e:
                with self._lock:
                    self.last_error = str(e)
                if self.orchestrator:
                    self.orchestrator._log(f"ERROR EN HILO: {e}")
            finally:
                with self._lock:
                    total_processed = self.total_processed
                    total_duplicates = self.total_duplicates
                    last_error = self.last_error
                    phones = getattr(
                        self.orchestrator, "callable_phones_found", 0
                    )
                try:
                    city_names = [
                        item.get("ciudad", "") if isinstance(item, dict) else str(item)
                        for item in ciudades
                    ]
                    with open_conn() as history_conn:
                        save_search_history(
                            ", ".join(city_names), pais, nicho,
                            (
                                "Lista para llamar"
                                if cold_call_mode
                                else "Deep Scan" if deep else "Normal"
                            ),
                            total_processed, total_duplicates, history_conn,
                            product_campaign=product_campaign,
                            target_segments=target_segments,
                            mision_id=self.mision_id,
                        )
                except Exception as history_error:
                    if self.orchestrator:
                        self.orchestrator._log(f"No se pudo guardar el historial: {history_error}")
                invalidate_leads_cache()
                if loop is not None:
                    loop.close()
                with self._lock:
                    self.last_summary = {
                        "leads": total_processed,
                        "dupes": total_duplicates,
                        "phones": phones,
                        "error": last_error,
                    }
                    # Se marca terminada solo después de cerrar DB/caché/event loop.
                    self.running = False

        self._thread = threading.Thread(target=_target, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        with self._lock:
            orchestrator = self.orchestrator
        if orchestrator:
            orchestrator.stop()
        # El worker es quien cambia `running` en su `finally`. Mantenerlo en True
        # durante la cancelación impide iniciar otra misión sobre el mismo estado
        # mientras el hilo anterior todavía está cerrando Chromium y la BD.

import streamlit as st
import asyncio
import threading
from engine.orchestrator import Orchestrator
from services.constants import NICHOS_DICT

class SearchMission:
    def __init__(self):
        self.running = False
        self.orchestrator = None
        self.total_processed = 0
        self._thread = None

    def start(self, sources, callback, nicho, ciudades, deep, limit, is_barrido, hunter_mode=False):
        def count_cb(n): 
            # Si n es un objeto Lead, incrementamos en 1. Si es int, usamos su valor.
            increment = 1 if not isinstance(n, int) else n
            self.total_processed += increment
            if 'total_session' not in st.session_state: st.session_state.total_session = 0
            st.session_state.total_session += increment
        
        self.orchestrator = Orchestrator(sources, log_callback=callback, lead_callback=count_cb)
        self.running = True
        self.total_processed = 0
        
        def _target():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if is_barrido:
                    sectores_reales = [k for k in NICHOS_DICT.keys() if "TODO EL MERCADO" not in k]
                    self.orchestrator._log(f"🚨 BARRIDO TOTAL ACTIVADO. Escaneando {len(sectores_reales)} sectores principales...")
                    for sector in sectores_reales:
                        if self.orchestrator.stop_requested: break
                        self.orchestrator._log(f"📂 Procesando Sector: {sector}")
                        loop.run_until_complete(self.orchestrator.buscar_todos(sector, ciudades, deep_scan=deep, limit=limit, hunter_mode=hunter_mode))
                else:
                    self.orchestrator._log(f"🔍 Objetivo: '{nicho}'")
                    loop.run_until_complete(self.orchestrator.buscar_todos(nicho, ciudades, deep_scan=deep, limit=limit, hunter_mode=hunter_mode))
                
                self.orchestrator._log(f"✨ Misión finalizada con éxito.")
            except Exception as e:
                if self.orchestrator:
                    self.orchestrator._log(f"❌ ERROR EN HILO: {e}")
            finally:
                self.running = False
                loop.close()

        from streamlit.runtime.scriptrunner import add_script_run_ctx
        self._thread = threading.Thread(target=_target, daemon=True)
        add_script_run_ctx(self._thread)
        self._thread.start()

    def stop(self):
        if self.orchestrator:
            self.orchestrator.stop()
        self.running = False

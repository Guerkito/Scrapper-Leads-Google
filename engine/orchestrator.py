import asyncio
import os
import random
from typing import List
from sources.base_source import BaseSource, Lead
from engine.query_expander import expandir_query
from engine.deduplicator import Deduplicator
from engine.web_extractor import extract_deep_data
from db import open_conn, save_lead, init_db

from playwright.async_api import async_playwright
from scraper import BROWSER_ARGS

class Orchestrator:
    def __init__(self, fuentes: List[BaseSource], log_callback=None, lead_callback=None):
        self.fuentes = fuentes
        self.deduplicator = Deduplicator()
        self.log_callback = log_callback
        self.lead_callback = lead_callback 
        self.stop_requested = False 
        
        # Reducimos concurrencia para evitar CAPTCHAs masivos
        max_concurrent = int(os.getenv("MAX_CONCURRENT", 2))
        self.semaphore = asyncio.Semaphore(max_concurrent) 
        init_db() 

    def stop(self):
        """Solicita la detención de la misión."""
        self.stop_requested = True
        self._log("🛑 Solicitud de parada recibida. Abortando misión...")

    def _log(self, msg):
        print(msg)
        if self.log_callback:
            self.log_callback(msg)

    async def buscar_fuente(self, fuente: BaseSource, queries: List[str], ciudad: str, context, limit: int = 20) -> List[Lead]:
        """Lanza búsqueda para una fuente con manejo de errores y múltiples queries."""
        resultados_fuente = []
        for q in queries:
            if self.stop_requested: break
            async with self.semaphore:
                if self.stop_requested: break
                
                # Retardo humano aleatorio para evitar detección
                await asyncio.sleep(random.uniform(2.0, 5.0))
                
                try:
                    self._log(f"🔍 [{fuente.__class__.__name__}] Buscando: {q} en {ciudad}...")
                    
                    def _on_lead_captured(lead_obj):
                        if self.stop_requested: return
                        try:
                            conn = open_conn()
                            if save_lead(lead_obj, conn):
                                conn.commit()
                                if self.lead_callback:
                                    self.lead_callback(lead_obj)
                            conn.close()
                        except Exception as e:
                            self._log(f"⚠️ Error guardando lead: {e}")

                    leads = await fuente.buscar(
                        query=q, 
                        ciudad=ciudad, 
                        context=context, 
                        limit=limit, 
                        lead_callback=_on_lead_captured,
                        stop_check=lambda: self.stop_requested
                    )
                    if self.stop_requested: break
                    resultados_fuente.extend(leads)
                except Exception as e:
                    if not self.stop_requested:
                        self._log(f"❌ Error en fuente {fuente.__class__.__name__} con query '{q}': {e}")
        return resultados_fuente

    async def buscar_todos(self, nicho_input: str, ciudades: List[str], deep_scan: bool = False, limit: int = 20, hunter_mode: bool = False) -> List[Lead]:
        """
        Coordina el proceso completo para múltiples ciudades y modo Deep Scan.
        """
        if self.stop_requested: return []
        self._log(f"🧠 Preparando inteligencia de búsqueda para: {nicho_input}")
        queries = await expandir_query(nicho_input)
        if self.stop_requested: return []
        
        if hunter_mode:
            self._log("🎯 MODO HUNTER ACTIVADO: Solo se capturarán leads SIN sitio web.")
            
        self._log(f"🚀 Iniciando misión multi-ciudad. Variaciones de búsqueda: {len(queries)}")

        async with async_playwright() as p:
            if self.stop_requested: return []
            browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = await browser.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
            
            todos_los_leads_brutos = []
            
            for ciudad in ciudades:
                if self.stop_requested: break
                
                puntos_gps = [ciudad]
                if deep_scan:
                    from city_coords import generate_grid, CITY_COORDS
                    if ciudad in CITY_COORDS:
                        grid = generate_grid(ciudad, grid_n=3)
                        if grid:
                            puntos_gps = grid
                            self._log(f"📍 [DEEP SCAN] Generados {len(grid)} puntos GPS para {ciudad}")

                # Ejecutamos secuencialmente por punto GPS/Fuente para no saturar y permitir parada real
                for punto in puntos_gps:
                    if self.stop_requested: break
                    for f in self.fuentes:
                        if self.stop_requested: break
                        fname = f.__class__.__name__.lower()
                        
                        # Cada llamada a buscar_fuente ya maneja su propio semáforo interno para queries
                        res = await self.buscar_fuente(f, queries, punto, context, limit=limit)
                        todos_los_leads_brutos.extend(res)
            
            await browser.close()
        
        if self.stop_requested: 
            self._log("🛑 Misión abortada con éxito.")
            return []
        
        # Enriquecimiento (Deep Scraping)
        leads_a_enriquecer = [l for l in todos_los_leads_brutos if l.tiene_web and l.sitio_web]
        
        if leads_a_enriquecer and not self.stop_requested:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    ignore_https_errors=True
                )
                
                for lead in leads_a_enriquecer:
                    if self.stop_requested: break
                    async with self.semaphore:
                        lead_enriquecido = await extract_deep_data(lead, context)
                        conn = open_conn()
                        save_lead(lead_enriquecido, conn)
                        conn.commit()
                        conn.close()
                
                await browser.close()

        self._log(f"✨ Misión completada.")
        return todos_los_leads_brutos

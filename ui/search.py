import streamlit as st
import datetime
import time
import asyncio
import threading
import sqlite3
import pandas as pd
from engine.orchestrator import Orchestrator
from sources.google_maps import GoogleMapsSource
from sources.rues import RUESSource
from sources.paginas_amarillas import PaginasAmarillasSource
from sources.linkedin import LinkedInSource
from geo_data import GEO_DATA
from db import DB_PATH
from services.constants import NICHOS_DICT
from services.search_mission import SearchMission

def render_search_view():
    if 'MISSION' not in st.session_state:
        st.session_state.MISSION = SearchMission()
    MISSION = st.session_state.MISSION

    st.markdown("""
        <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 20px;'>
            <h2 style='margin: 0;'>🚀 Motor de Inteligencia Universal</h2>
            <span style='background: rgba(255,0,0,0.1); color: #FF0000; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; border: 1px solid rgba(255,0,0,0.2);'>Onyx Engine v3.0</span>
        </div>
    """, unsafe_allow_html=True)
    
    with st.container(border=True):
        barrido_total = st.checkbox("🌎 MODO BARRIDO TOTAL", help="Ignora tus etiquetas y busca absolutamente todas las empresas de todos los sectores en las ciudades elegidas.")
        if barrido_total:
            st.warning("⚠️ El Barrido Total ignorará tus etiquetas y buscará en todos los sectores estratégicos.")
            
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🎯 Configuración del Objetivo")
            modo_input = st.toggle("✍️ Escritura libre con IA", value=True, help="Activa esto para escribir cualquier cosa y que la IA la expanda.")
            
            if not modo_input:
                cat_pre = st.selectbox("Selecciona un sector estratégico", list(NICHOS_DICT.keys()), disabled=barrido_total)
                nicho_pre = st.selectbox("Nicho específico", NICHOS_DICT[cat_pre], disabled=barrido_total)
                query_input = nicho_pre
            else:
                if 'query_tags' not in st.session_state: st.session_state.query_tags = []
                
                st.markdown("<p style='font-size:0.75rem; color:#6A6A7A; margin-bottom:5px;'>Sugerencias Rápidas:</p>", unsafe_allow_html=True)
                quick_niches = ["Colegios", "Odontólogos", "Restaurantes", "Fábricas", "Inmobiliarias"]
                q_cols = st.columns(len(quick_niches))
                for idx, qn in enumerate(quick_niches):
                    if q_cols[idx].button(qn, key=f"quick_{qn}", width="stretch", disabled=barrido_total):
                        if qn not in st.session_state.query_tags:
                            st.session_state.query_tags.append(qn)
                            st.rerun()

                all_suggestions = sorted(list(set([n for sublist in NICHOS_DICT.values() for n in sublist])))
                selected_tags = st.multiselect(
                    "Objetivos de búsqueda",
                    options=sorted(list(set(all_suggestions + st.session_state.query_tags))),
                    default=st.session_state.query_tags,
                    disabled=barrido_total
                )
                st.session_state.query_tags = selected_tags
                new_tag = st.text_input("➕ Término personalizado", key="new_tag_input", disabled=barrido_total, autocomplete="off")
                if new_tag:
                    clean_tag = new_tag.strip()
                    if clean_tag and clean_tag not in st.session_state.query_tags:
                        st.session_state.query_tags.append(clean_tag)
                        st.rerun()
                
                query_input = ", ".join(st.session_state.query_tags)
            
        with col2:
            st.markdown("#### 📍 Geografía y Fuentes")
            paises = sorted(GEO_DATA.keys())
            def_idx = paises.index(st.session_state.pais_sel) if st.session_state.pais_sel in paises else 0
            pais_sel = st.selectbox("País de búsqueda", paises, index=def_idx, key="pais_sel_widget")
            st.session_state.pais_sel = pais_sel
            
            todos_municipios = []
            for depto in GEO_DATA[pais_sel].values():
                todos_municipios.extend(depto)
            
            ciudades_sel = st.multiselect(
                "Ciudades / Municipios", 
                options=sorted(list(set(todos_municipios))),
                default=["Bogotá"] if "Bogotá" in todos_municipios else []
            )
            
            fuentes_opciones = {
                "Maps": GoogleMapsSource(), 
                "Páginas Amarillas": PaginasAmarillasSource(),
                "LinkedIn": LinkedInSource()
            }
            # RUES removido o marcado como próximamente si no es funcional
            # fuentes_opciones["RUES"] = RUESSource() 
            
            fuentes_sel = st.multiselect("Fuentes de Inteligencia", list(fuentes_opciones.keys()), default=["Maps"])
            
        st.divider()
        st.markdown("#### ⚙️ Parámetros Avanzados")
        c2a, c2b, c2c, c2d = st.columns([1, 1, 1, 2])
        with c2a:
            limit_sel = st.number_input("Límite por zona", 5, 500, 20)
        with c2b:
            deep_scan = st.toggle("🛰️ Modo Deep Scan", help="Barrido GPS de alta precisión.")
        with c2c:
            hunter_mode = st.toggle("🎯 Filtro: Sin Sitio Web", help="Captura SOLO leads que no tienen página web.")
        with c2d:
            st.markdown("<p style='font-size:0.75rem; color:#6A6A7A;'>Favoritos</p>", unsafe_allow_html=True)
            conn_fav = sqlite3.connect(DB_PATH)
            try:
                favs = pd.read_sql_query("SELECT * FROM search_favorites", conn_fav)
            except:
                favs = pd.DataFrame()
            conn_fav.close()
            if not favs.empty:
                selected_fav = st.selectbox("Cargar configuración", ["Seleccionar..."] + favs['nombre'].tolist(), label_visibility="collapsed")
                if selected_fav != "Seleccionar...":
                    pass
            
        if MISSION.running:
            with st.container(border=True):
                mc1, mc2 = st.columns([2, 1])
                with mc1:
                    st.markdown(f"### ⚡ MISIÓN EN CURSO")
                    st.write(f"Capturando datos en segundo plano... No cierres esta ventana.")
                with mc2:
                    if st.button("🛑 ABORTAR MISIÓN", type="primary", width="stretch"):
                        MISSION.stop()
                        st.rerun()
                
                st.markdown(
                    f"<div style='background:#0C0C0E; border-left: 5px solid #FF0000; padding: 15px; margin: 15px 0;'>"
                    f"<span style='color:#6A6A7A; font-size:0.8rem; text-transform:uppercase;'>Leads Capturados en esta sesión</span><br>"
                    f"<span style='font-size:2.5rem; font-weight:800; color:#FF0000;'>{MISSION.total_processed}</span>"
                    f"</div>", 
                    unsafe_allow_html=True
                )
                
                if st.session_state.get('console_logs'):
                    logs = "\n".join(st.session_state.console_logs[-8:])
                    st.markdown(f"<div class='console-box' style='height:150px;'>{logs}</div>", unsafe_allow_html=True)
                
                time.sleep(2)
                st.rerun()

        if not MISSION.running:
            if st.button("🔥 INICIAR MISIÓN DE EXTRACCIÓN", type="primary", width="stretch"):
                final_query = "TODAS LAS EMPRESAS" if barrido_total else query_input
                
                if (final_query or barrido_total) and ciudades_sel and fuentes_sel:
                    st.session_state.console_logs = []
                    
                    def update_console(msg):
                        try:
                            if 'console_logs' not in st.session_state: st.session_state.console_logs = []
                            st.session_state.console_logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")
                        except Exception:
                            # Ignorar errores al actualizar el log de consola en el hilo
                            pass

                    fuentes_instancias = [fuentes_opciones[f] for f in fuentes_sel]
                    
                    MISSION.start(
                        fuentes_instancias, 
                        update_console, 
                        final_query, 
                        ciudades_sel, 
                        deep_scan, 
                        limit_sel, 
                        barrido_total,
                        hunter_mode=hunter_mode
                    )
                    st.rerun()
                else:
                    st.warning("Completa los campos necesarios para iniciar.")

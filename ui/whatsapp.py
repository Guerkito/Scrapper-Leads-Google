import streamlit as st
import threading
import os
import requests
from services.campaigns import CampState, campaign_worker
from services.constants import COUNTRY_CODES

def render_whatsapp_view(df_all):
    st.markdown("### 🚀 Campañas de WhatsApp (Evolution API)")
    
    if 'CAMP' not in st.session_state:
        st.session_state.CAMP = CampState()
    CAMP = st.session_state.CAMP

    evo_url = os.getenv("EVO_URL", "http://127.0.0.1:8080").strip().rstrip("/")
    evo_key = os.getenv("EVO_API_KEY", "")
    evo_instance = st.session_state.get("evo_instance_name", "onyxbot")
    pais_sel = st.session_state.get('pais_sel', 'Colombia')

    with st.container(border=True):
        st.markdown("#### ⚙️ Configuración de Envío")
        c1, c2 = st.columns(2)
        with c1:
            msg_template = st.text_area(
                "Plantilla de Mensaje",
                "Hola {nombre}, vi tu negocio en Google Maps y me encantó. "
                "Soy de Onyx Intelligence y me gustaría ayudarte a conseguir más clientes. "
                "¿Tienes un momento para hablar?",
                height=150,
                help="Usa {nombre} para personalizar el mensaje."
            )
        with c2:
            leads_target = st.multiselect(
                "Filtrar leads para campaña",
                options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Sin WhatsApp"],
                default=["Interesado"]
            )
            test_mode = st.toggle("🧪 Modo Simulación (sin envíos reales)", value=True)
            
            df_camp = df_all[df_all['estado'].isin(leads_target)]
            st.metric("Leads en cola", len(df_camp))

    if CAMP.running:
        st.divider()
        st.warning("⚡ Campaña en curso...")
        st.progress(CAMP.progress)
        
        if CAMP.countdown > 0:
            st.info(f"⏳ Próximo envío en {CAMP.countdown} segundos...")
        
        # Logs de la campaña
        with st.expander("Ver logs de campaña", expanded=True):
            for level, msg in CAMP.logs[-10:]:
                if level == "info": st.caption(msg)
                elif level == "success": st.success(msg)
                elif level == "warning": st.warning(msg)
                elif level == "error": st.error(msg)
        
        if st.button("🛑 DETENER CAMPAÑA"):
            CAMP.stop = True
            st.rerun()
        
        st.empty()
        st.rerun() # Auto-refresh UI
    else:
        if st.button("🚀 INICIAR CAMPAÑA", type="primary", width="stretch"):
            if df_camp.empty:
                st.error("No hay leads seleccionados para la campaña.")
            elif not evo_url or not evo_key:
                st.error("Configura EVO_URL y EVO_API_KEY en el archivo .env")
            else:
                CAMP.reset()
                leads_list = df_camp.to_dict('records')
                
                t = threading.Thread(
                    target=campaign_worker,
                    args=(CAMP, leads_list, msg_template, evo_url, evo_instance, evo_key, pais_sel, test_mode),
                    daemon=True
                )
                from streamlit.runtime.scriptrunner import add_script_run_ctx
                add_script_run_ctx(t)
                t.start()
                st.rerun()

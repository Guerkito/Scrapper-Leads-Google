import streamlit as st
import threading
import pandas as pd
from config import EVO_URL, EVO_API_KEY, EVO_INSTANCE
from services.campaigns import CampState, campaign_worker
from services.phone_utils import normalize_phone
from ui.icons import title_html


@st.fragment(run_every=1)
def _campaign_monitor(campaign):
    if not campaign.running:
        if st.session_state.pop("wa_campaign_was_running", False):
            st.rerun()
        return
    st.session_state.wa_campaign_was_running = True
    st.warning("Campaña en curso...")
    st.progress(campaign.progress)
    if campaign.countdown > 0:
        st.info(f"Próximo envío en {campaign.countdown} segundos...")
    with st.expander("Ver logs de campaña", expanded=True):
        for level, msg in campaign.logs[-10:]:
            getattr(st, level if level in {"success", "warning", "error"} else "caption")(msg)
    if st.button("DETENER CAMPAÑA"):
        campaign.stop = True

def render_whatsapp_view(df_all):
    st.markdown(title_html("Campañas de WhatsApp (Evolution API)", "whatsapp", 3), unsafe_allow_html=True)

    if 'CAMP' not in st.session_state:
        st.session_state.CAMP = CampState()
    CAMP = st.session_state.CAMP

    evo_url = EVO_URL
    evo_key = EVO_API_KEY
    evo_instance = st.text_input(
        "Instancia de Evolution",
        value=st.session_state.get("evo_instance_name", EVO_INSTANCE),
        key="evo_instance_name",
        help="Nombre de la instancia configurada en Evolution API.",
    )
    pais_sel = st.session_state.get('pais_sel', 'Colombia')

    with st.container(border=True):
        st.markdown(title_html("Configuración de Envío", "settings", 4), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            msg_template = st.text_area(
                "Plantilla de Mensaje",
                "Hola {nombre}, vi tu negocio en Maps y detecté una oportunidad para convertir más búsquedas en clientes. "
                "Tengo una propuesta breve y concreta para mejorar tu presencia digital. ¿Te interesa que te la comparta?",
                height=150,
                help="Usa {nombre} para personalizar el mensaje."
            )
        with c2:
            leads_target = st.multiselect(
                "Filtrar leads para campaña",
                options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Sin WhatsApp"],
                default=["Interesado"]
            )
            test_mode = st.toggle("Modo Simulación (sin envíos reales)", value=True)
            only_without_web = st.toggle("Solo empresas sin página web", value=True)
            delay_min = st.number_input("Pausa mínima (seg)", 0, 600, 120, disabled=test_mode)
            delay_max = st.number_input("Pausa máxima (seg)", 0, 900, 300, disabled=test_mode)

            df_camp = df_all[df_all['estado'].isin(leads_target)].copy()
            if 'estado_contacto' in df_camp:
                df_camp = df_camp[
                    df_camp['estado_contacto'].fillna('').str.casefold() != 'no_contactar'
                ]
            if only_without_web:
                df_camp = df_camp[~df_camp['tiene_web'].fillna(False).astype(bool)]
            df_camp = df_camp[df_camp.apply(
                lambda row: bool(normalize_phone(
                    row.get('telefono_e164') if pd.notna(row.get('telefono_e164')) else row.get('telefono'),
                    row.get('pais') if pd.notna(row.get('pais')) else pais_sel,
                )), axis=1
            )]
            st.metric("Leads en cola", len(df_camp))

    if CAMP.running:
        st.divider()
        _campaign_monitor(CAMP)
    else:
        if st.button("INICIAR CAMPAÑA", type="primary", width="stretch"):
            if df_camp.empty:
                st.error("No hay leads seleccionados para la campaña.")
            elif not test_mode and (not evo_url or not evo_key):
                st.error("Configura EVO_URL y EVO_API_KEY en el archivo .env")
            else:
                CAMP.reset()
                leads_list = df_camp.to_dict('records')
                
                t = threading.Thread(
                    target=campaign_worker,
                    args=(CAMP, leads_list, msg_template, evo_url, evo_instance, evo_key, pais_sel, test_mode, (delay_min, delay_max)),
                    daemon=True
                )
                t.start()
                st.rerun()

import streamlit as st
import threading
from config import email_settings
from services.campaigns import CampState
from services.email_service import email_campaign_worker
from ui.icons import title_html


@st.fragment(run_every=1)
def _email_campaign_monitor(campaign):
    if not campaign.running:
        if st.session_state.pop("email_campaign_was_running", False):
            st.rerun()
        return
    st.session_state.email_campaign_was_running = True
    st.warning("Campaña de email en curso...")
    st.progress(campaign.progress)
    if campaign.countdown > 0:
        st.info(f"Próximo envío en {campaign.countdown} segundos...")
    with st.expander("Registro de actividad", expanded=True):
        for level, msg in campaign.logs[-12:]:
            getattr(st, level if level in {"success", "warning", "error"} else "caption")(msg)
    if st.button("DETENER CAMPAÑA", type="secondary", width="stretch"):
        campaign.stop = True

def render_email_view(df_all):
    """Renderiza la vista de campañas de Email Marketing."""
    st.markdown(title_html("Email Marketing (Onyx Engine)", "mail", 3), unsafe_allow_html=True)

    # Inicializar estado de la campaña si no existe
    if 'EMAIL_CAMP' not in st.session_state:
        st.session_state.EMAIL_CAMP = CampState()
    
    CAMP = st.session_state.EMAIL_CAMP

    # Contenedor principal de configuración
    with st.container(border=True):
        st.markdown(title_html("Configuración de Campaña", "settings", 4), unsafe_allow_html=True)
        
        c1, c2 = st.columns([2, 1])
        
        with c1:
            subject = st.text_input(
                "Asunto del Correo", 
                "Propuesta estratégica para {nombre} 🚀",
                help="Puedes usar {nombre} para personalizar el asunto."
            )
            
            msg_template = st.text_area(
                "Plantilla del Cuerpo (Soporta HTML)",
                "Hola <b>{nombre}</b>,<br><br>"
                "He visto tu negocio de <i>{nicho}</i> en Google Maps y me ha parecido excelente la puntuación de {rating} que tienes en {ciudad}.<br><br>"
                "Sin embargo, he notado algunas oportunidades de mejora en tu presencia digital que podrían ayudarte a conseguir más clientes este mes.<br><br>"
                "¿Tendrías 5 minutos para una breve llamada mañana?<br><br>"
                "Atentamente,<br>"
                "<b>Equipo de Crecimiento Onyx</b>",
                height=300,
                help="Variables disponibles: {nombre}, {nicho}, {ciudad}, {rating}"
            )
            
        with c2:
            st.info("💡 **Segmentación Inteligente**\nSolo se procesarán leads que tengan un email válido detectado por el scraper.")
            
            # Filtrar leads que tienen email real
            df_with_email = df_all[
                df_all['email'].notna() & 
                (df_all['email'] != '') & 
                (df_all['email'].str.contains('@', na=False)) &
                (~df_all['email'].str.lower().isin(['none', 'n/a', 'null']))
            ]
            
            leads_target = st.multiselect(
                "Filtrar por estado del lead",
                options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Sin WhatsApp"],
                default=["Nuevo", "Sin WhatsApp"]
            )
            
            test_mode = st.toggle("🧪 Modo Simulación", value=True, help="Si está activo, no se enviarán correos reales.")
            
            # Aplicar filtros
            df_camp = df_with_email[df_with_email['estado'].isin(leads_target)]
            if 'estado_contacto' in df_camp:
                df_camp = df_camp[
                    df_camp['estado_contacto'].fillna('').str.casefold() != 'no_contactar'
                ]
            
            st.metric("Leads en cola de envío", len(df_camp))
            
            _mail_cfg = email_settings()
            if not test_mode and (not _mail_cfg["user"] or not _mail_cfg["pass"]):
                st.warning("⚠️ **Falta Configuración**\nConfigura EMAIL_USER y EMAIL_PASS en el archivo .env para habilitar envíos reales.")

    # Área de ejecución de campaña
    if CAMP.running:
        st.divider()
        _email_campaign_monitor(CAMP)
    else:
        # Botón para iniciar
        if st.button("✉️ INICIAR ENVÍO DE CORREOS", type="primary", width="stretch"):
            _mail_cfg = email_settings()
            if df_camp.empty:
                st.error("No hay leads con email que cumplan los criterios de filtrado.")
            elif not test_mode and (not _mail_cfg["user"] or not _mail_cfg["pass"]):
                st.error("Error: Debes configurar las credenciales SMTP en el archivo .env para realizar envíos reales.")
            else:
                CAMP.reset()
                leads_list = df_camp.to_dict('records')
                
                # Lanzar el worker en un hilo separado
                t = threading.Thread(
                    target=email_campaign_worker,
                    args=(CAMP, leads_list, subject, msg_template, test_mode),
                    daemon=True
                )
                
                t.start()
                st.rerun()

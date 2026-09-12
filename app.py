import streamlit as st
import datetime

import config  # carga .env y centraliza configuración
from db import init_db, DB_PATH
from ui.styles import apply_styles
from ui.dashboard import render_dashboard_view
from ui.search import render_search_view
from ui.crm import render_crm_view
from ui.map import render_map_view
from ui.analytics import render_analytics_view
from ui.whatsapp import render_whatsapp_view
from ui.email import render_email_view
from ui.admin import render_admin_view
from ui.icons import svg_icon
from ui.search_library import render_search_library_view
from services.leads import load_all_leads
from services.whatsapp_service import render_whatsapp_status_sidebar

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _initialize_database(database_path):
    """Inicializa esquema/migraciones una sola vez por proceso y base de datos."""
    init_db()
    return database_path


_initialize_database(DB_PATH)

if 'view'              not in st.session_state: st.session_state.view = "Búsqueda"
if 'total_session'     not in st.session_state: st.session_state.total_session = 0
if 'skipped_session'   not in st.session_state: st.session_state.skipped_session = 0
if 'pais_sel'          not in st.session_state: st.session_state.pais_sel = "Colombia"
if 'last_summary'      not in st.session_state: st.session_state.last_summary = None

# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="ONYX LeadGen", layout="wide")
apply_styles()

PAGE_META = {
    "Inicio": {
        "kicker": "Centro de mando", "title": "ONYX LeadGen",
        "subtitle": "Encuentra, prioriza y contacta clientes potenciales.",
        "icon": "dashboard",
    },
    "Búsqueda": {
        "kicker": "Exploración", "title": "Buscar clientes",
        "subtitle": "Define qué vendes, a quién buscas y en qué zona. ONYX prepara la lista y el argumento comercial.",
        "icon": "search",
    },
    "Búsquedas": {
        "kicker": "Gestión", "title": "Búsquedas guardadas",
        "subtitle": "Entra a cada búsqueda: CRM, mapa, analítica y campañas de esa lista. También puedes borrarla.",
        "icon": "folder",
    },
    "CRM": {
        "kicker": "Gestión", "title": "Leads y oportunidades",
        "subtitle": "Filtra, prioriza y abre cada prospecto para preparar el contacto.",
        "icon": "crm",
    },
    "Mapa": {
        "kicker": "Gestión", "title": "Inteligencia geográfica",
        "subtitle": "Ubica cada oportunidad en el territorio y huele las zonas calientes.",
        "icon": "map",
    },
    "Analítica": {
        "kicker": "Gestión", "title": "Rendimiento",
        "subtitle": "Métricas de captura, calidad de datos y madurez digital de la base.",
        "icon": "chart",
    },
    "WhatsApp": {
        "kicker": "Comunicación", "title": "Campañas WhatsApp",
        "subtitle": "Envía con control anti-ban y automatiza respuestas con Evolution API + Ollama.",
        "icon": "whatsapp",
    },
    "Email": {
        "kicker": "Comunicación", "title": "Campañas de correo",
        "subtitle": "Personaliza plantillas por lead y dispara con pausas de seguridad.",
        "icon": "mail",
    },
    "Admin": {
        "kicker": "Sistema", "title": "Administración",
        "subtitle": "Auditoría, respaldos, importación y configuración del sistema.",
        "icon": "settings",
    },
}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div class='onyx-logo'>
            <span class='l1'>LeadGen</span>
            <span class='l2'>ONYX</span>
        </div>
        <div class='onyx-version'>Prospección comercial</div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown("<p class='sidebar-label'>Exploración</p>", unsafe_allow_html=True)

    def _nav(view_id):
        st.session_state.view = view_id

    nav_sections = [
        ("Exploración", [("Inicio", "Inicio"), ("Buscar clientes", "Búsqueda")]),
        ("Gestión", [("Búsquedas", "Búsquedas"), ("CRM", "CRM"), ("Mapa", "Mapa"), ("Analítica", "Analítica")]),
        ("Comunicación", [("WhatsApp", "WhatsApp"), ("Email", "Email")]),
    ]
    for section_title, items in nav_sections:
        if section_title != "Exploración":
            st.markdown(
                "<div style='height:14px'></div>", unsafe_allow_html=True,
            )
            st.markdown(f"<p class='sidebar-label'>{section_title}</p>", unsafe_allow_html=True)
        for label, view_id in items:
            st.button(
                label,
                key=f"nav_{view_id}",
                width="stretch",
                type="primary" if st.session_state.view == view_id else "secondary",
                on_click=_nav,
                args=(view_id,),
            )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown("<p class='sidebar-label'>Sistema</p>", unsafe_allow_html=True)
    st.button(
        "Administración", key="nav_admin", width="stretch",
        type="primary" if st.session_state.view == "Admin" else "secondary",
        on_click=_nav, args=("Admin",),
    )

    st.divider()
    st.markdown("<p class='sidebar-label'>Conexiones</p>", unsafe_allow_html=True)
    render_whatsapp_status_sidebar()

    st.caption(f"ONYX © {datetime.date.today().year}")

# ---------------------------------------------------------------------------
# View header
# ---------------------------------------------------------------------------
view_mode = st.session_state.view
meta = PAGE_META.get(view_mode, PAGE_META["Inicio"])
st.markdown(
    f"<div class='page-kicker' style='display:flex;align-items:center;gap:6px'>{svg_icon(meta['icon'], 12)} {meta['kicker']}</div>"
    f"<div class='onyx-header'>{meta['title']}</div>"
    f"<div class='onyx-subtitle'>{meta['subtitle']}</div>",
    unsafe_allow_html=True,
)

df_all = load_all_leads()

# ---------------------------------------------------------------------------
# Main Content area
# ---------------------------------------------------------------------------
if view_mode == "Inicio":
    render_dashboard_view(df_all)
elif view_mode == "Búsqueda":
    render_search_view()
elif view_mode == "Búsquedas":
    render_search_library_view()
elif view_mode == "CRM":
    render_crm_view(df_all)
elif view_mode == "Mapa":
    render_map_view(df_all)
elif view_mode == "Analítica":
    render_analytics_view(df_all)
elif view_mode == "WhatsApp":
    render_whatsapp_view(df_all)
elif view_mode == "Email":
    render_email_view(df_all)
elif view_mode == "Admin":
    render_admin_view()

# Consolidación del resumen de misión en cualquier pestaña: si una misión de
# fondo terminó (aunque el usuario navegó a CRM/Mapa/otra vista), sumamos sus
# resultados y mostramos el toast en el próximo rerun.
_mission = st.session_state.get("MISSION")
if _mission is not None:
    _mstate = _mission.snapshot()
    _was_running = st.session_state.get("_mission_was_running_prev", False)
    if _was_running and not _mstate["running"]:
        _summary = _mstate.get("last_summary") or {}
        st.session_state.total_session += int(_summary.get("leads") or 0)
        st.session_state.skipped_session += int(_summary.get("dupes") or 0)
        st.session_state.last_summary = _summary
    st.session_state._mission_was_running_prev = _mstate["running"]

# Alerts / Summary
if st.session_state.last_summary:
    s = st.session_state.last_summary
    st.toast(f"Misión completada: {s['leads']} capturados, {s['dupes']} duplicados.")
    st.session_state.last_summary = None

import streamlit as st
import datetime

import config  # carga .env y centraliza configuración
from db import init_db, DB_PATH
from ui.styles import apply_styles
from ui.search import render_search_view
from ui.crm import render_crm_view
from ui.map import render_map_view
from ui.analytics import render_analytics_view
from ui.whatsapp import render_whatsapp_view
from ui.email import render_email_view
from ui.admin import render_admin_view
from ui.helpers import overview_strip
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
st.set_page_config(page_title="Lead Gen ONYX", layout="wide")
apply_styles()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div class='onyx-logo'>
            LEAD GEN
            <span>ONYX</span>
        </div>
        <div class='onyx-version'>Prospección comercial &nbsp;·&nbsp; v3.0</div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown("<p class='sidebar-label'>Conexiones</p>", unsafe_allow_html=True)

    render_whatsapp_status_sidebar()

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    if st.button("Administración", width="stretch", type="secondary"):
        st.session_state.view = "Admin"

    st.divider()
    st.caption(f"ONYX © {datetime.date.today().year}")

# ---------------------------------------------------------------------------
# Header & Metrics
# ---------------------------------------------------------------------------
st.markdown("""
    <div class='onyx-header'>
        ONYX <span class='onyx-header-red'>LeadGen</span>
    </div>
    <div class='onyx-subtitle'>Encuentra, prioriza y contacta clientes potenciales</div>
""", unsafe_allow_html=True)

df_all = load_all_leads()

if not df_all.empty:
    oro_count = len(df_all[df_all['calificacion'] == 'oro'])
    if 'telefono_e164' in df_all.columns:
        callable_count = df_all['telefono_e164'].fillna("").astype(str).str.startswith("+").sum()
    else:
        callable_count = df_all['telefono'].fillna("").astype(str).str.len().ge(7).sum()
else:
    oro_count, callable_count = 0, 0

# ---------------------------------------------------------------------------
# Navbar
# ---------------------------------------------------------------------------
btns = [
    ("Buscar clientes", "Búsqueda"),
    ("CRM", "CRM"),
    ("Mapa", "Mapa"),
    ("Resultados", "Analytics"),
    ("WhatsApp", "WhatsApp"),
    ("Correo", "Email")
]

with st.container(key="main_navigation"):
    nav_cols = st.columns([1,1,1,1,1,1])

    def _navigate(view_id):
        st.session_state.view = view_id

    for i, (label, view_id) in enumerate(btns):
        is_active = st.session_state.view == view_id
        nav_cols[i].button(
            label,
            width="stretch",
            key=f"nav_{view_id}",
            type="primary" if is_active else "secondary",
            on_click=_navigate,
            args=(view_id,),
        )

st.markdown(
    overview_strip([
        ("Base de leads", f"{len(df_all):,}", "total guardado"),
        ("Listos para llamar", f"{int(callable_count):,}", "teléfono válido"),
        ("Alta prioridad", f"{oro_count:,}", "calificación oro"),
        ("Esta sesión", f"{st.session_state.total_session:,}", "leads nuevos"),
    ]),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Main Content area
# ---------------------------------------------------------------------------
view_mode = st.session_state.view

if view_mode == "Búsqueda":
    render_search_view()
elif view_mode == "CRM":
    render_crm_view(df_all)
elif view_mode == "Mapa":
    render_map_view(df_all)
elif view_mode == "Analytics":
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

import streamlit as st
import os
import sqlite3
import pandas as pd
import requests
import datetime
import time
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from db import init_db, DB_PATH
from ui.styles import apply_styles
from ui.search import render_search_view
from ui.crm import render_crm_view
from ui.map import render_map_view
from ui.analytics import render_analytics_view
from ui.whatsapp import render_whatsapp_view
from ui.admin import render_admin_view
from ui.helpers import kpi_card
from services.leads import get_wa_link, get_score, load_all_leads
from services.constants import STATUS_COLORS
from services.whatsapp_service import render_whatsapp_status_sidebar

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
init_db()

if 'view'              not in st.session_state: st.session_state.view = "🌍 Búsqueda"
if 'total_session'     not in st.session_state: st.session_state.total_session = 0
if 'skipped_session'   not in st.session_state: st.session_state.skipped_session = 0
if 'pais_sel'          not in st.session_state: st.session_state.pais_sel = "Colombia"
if 'last_summary'      not in st.session_state: st.session_state.last_summary = None

# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Lead Gen ONYX", layout="wide", page_icon="⬛")
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
        <div class='onyx-version'>Intelligence Platform &nbsp;·&nbsp; v3.0</div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown("<p style='font-size:0.7rem; font-weight:600; letter-spacing:0.1em; color:#6A6A7A; text-transform:uppercase; margin-bottom:10px;'>Estado del Sistema</p>", unsafe_allow_html=True)

    render_whatsapp_status_sidebar()

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    if st.button("⚙️ Administración", use_container_width=True, type="secondary"):
        st.session_state.view = "⚙️ Admin"
        st.rerun()

    st.divider()
    st.caption("Onyx Intelligence Platform © 2024")

# ---------------------------------------------------------------------------
# Header & Metrics
# ---------------------------------------------------------------------------
st.markdown("""
    <div class='onyx-header'>
        LEAD GEN &nbsp;<span class='onyx-header-red'>ONYX</span>
    </div>
    <div class='onyx-subtitle'>Prospección inteligente &nbsp;·&nbsp; Google Maps Intelligence</div>
""", unsafe_allow_html=True)

df_all = load_all_leads()

# KPIs principales
r1a, r1b, r1c = st.columns(3)
r1a.markdown(kpi_card("Leads capturados", st.session_state.total_session, "#FF0000", "nuevos esta sesión"), unsafe_allow_html=True)
r1b.markdown(kpi_card("Duplicados omitidos", st.session_state.skipped_session, "#555568", "ya existían en la DB"), unsafe_allow_html=True)
r1c.markdown(kpi_card("Total en base de datos", len(df_all), "#FF0000"), unsafe_allow_html=True)

# Tarjetas secundarias (Restauradas según petición del usuario)
st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

if not df_all.empty:
    oro_count = len(df_all[df_all['calificacion'] == 'oro'])
    web_pct = (df_all['tiene_web'].sum() / len(df_all)) * 100 if len(df_all) > 0 else 0

    def _parse_rating(x):
        try:
            return float(str(x).split('/')[0].strip()) if x and '/' in str(x) else 0
        except: return 0
    avg_rating = df_all['rating'].apply(_parse_rating).mean()
    top_city = df_all['ciudad'].value_counts().idxmax() if 'ciudad' in df_all.columns and not df_all['ciudad'].dropna().empty else "N/A"
else:
    oro_count, web_pct, avg_rating, top_city = 0, 0, 0, "N/A"

c1.markdown(kpi_card("Leads Oro 🏆", f"{oro_count}", "#F5C518"), unsafe_allow_html=True)
c2.markdown(kpi_card("Adopción Web 🌐", f"{round(web_pct)}%", "#4ADE80"), unsafe_allow_html=True)
c3.markdown(kpi_card("Rating Promedio ⭐", f"{round(avg_rating, 1)}", "#FF0000"), unsafe_allow_html=True)
c4.markdown(kpi_card("Top Ciudad 📍", f"{top_city}", "#FFFFFF"), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Navbar
# ---------------------------------------------------------------------------
nav_cols = st.columns([1,1,1,1,1])
btns = [
    ("🌍 Búsqueda", "🌍 Búsqueda"),
    ("📝 CRM", "📝 CRM"),
    ("🗺️ Mapa", "🗺️ Mapa"),
    ("📊 Analytics", "📊 Analytics"),
    ("🚀 WhatsApp", "🚀 WhatsApp")
]

for i, (label, view_id) in enumerate(btns):
    is_active = st.session_state.view == view_id
    if nav_cols[i].button(
        label,
        use_container_width=True,
        key=f"nav_{view_id}",
        type="primary" if is_active else "secondary",
    ):
        st.session_state.view = view_id
        st.rerun()

# ---------------------------------------------------------------------------
# Main Content area
# ---------------------------------------------------------------------------
view_mode = st.session_state.view

if view_mode == "🌍 Búsqueda":
    render_search_view()
elif view_mode == "📝 CRM":
    render_crm_view(df_all)
elif view_mode == "🗺️ Mapa":
    render_map_view(df_all)
elif view_mode == "📊 Analytics":
    render_analytics_view(df_all)
elif view_mode == "🚀 WhatsApp":
    render_whatsapp_view(df_all)
elif view_mode == "⚙️ Admin":
    render_admin_view()

# Alerts / Summary
if st.session_state.last_summary:
    s = st.session_state.last_summary
    st.toast(f"Misión completada: {s['leads']} capturados, {s['dupes']} duplicados.")
    st.session_state.last_summary = None

import streamlit as st
import asyncio
import threading
import datetime
import urllib.parse
import sqlite3
import pandas as pd
from geo_data import GEO_DATA
from db import DB_PATH, init_db
from scraper import main_loop

# ---------------------------------------------------------------------------
# Nichos — nivel módulo para evitar recrearlos en cada rerun
# ---------------------------------------------------------------------------
NICHOS_DICT = {
    "🌎 TODO EL MERCADO": ["TODOS LOS NEGOCIOS (Barrido Total)", "Empresas locales", "Servicios profesionales"],
    "🏥 SALUD & MEDICINA": ["TODOS LOS SUBNICHOS (Sector Salud)", "Odontólogos", "Clínicas Médicas", "Psicólogos", "Fisioterapeutas", "Ópticas", "Dermatólogos", "Ginecólogos", "Pediatras", "Veterinarias"],
    "🍽️ GASTRONOMÍA & OCIO": ["TODOS LOS SUBNICHOS (Sector Gastro)", "Restaurantes", "Cafeterías", "Pizzerías", "Hamburgueserías", "Panaderías", "Bares", "Sushi", "Comida Vegana"],
    "🚗 SECTOR AUTOMOTRIZ": ["TODOS LOS SUBNICHOS (Sector Motor)", "Talleres Mecánicos", "Concesionarios", "Venta de Repuestos", "Lavado de Autos", "Centros de Diagnóstico", "Motos"],
    "🏠 CONSTRUCCIÓN & HOGAR": ["TODOS LOS SUBNICHOS (Sector Hogar)", "Inmobiliarias", "Arquitectos", "Constructoras", "Ferreterías", "Reformas", "Cerrajeros", "Mueblerías"],
    "💄 BELLEZA & BIENESTAR": ["TODOS LOS SUBNICHOS (Sector Belleza)", "Peluquerías", "Barberías", "Spas", "Centros de Uñas", "Gimnasios", "Yoga", "Tatuajes"],
    "⚖️ PROFESIONALES & LEGAL": ["TODOS LOS SUBNICHOS (Sector Profesional)", "Abogados", "Contadores", "Notarías", "Asesores Fiscales", "Agencias de Seguros", "Agencias de Marketing"],
    "🏗️ INDUSTRIAL & TÉCNICO": ["TODOS LOS SUBNICHOS (Sector Industrial)", "Fábricas", "Logística", "Mantenimiento", "Control de Plagas", "Textiles", "Metalúrgicas"],
    "🎓 EDUCACIÓN": ["TODOS LOS SUBNICHOS (Sector Educación)", "Colegios", "Jardines Infantiles", "Academias de Idiomas", "Universidades", "Escuelas de Conducción"],
    "💻 TECNOLOGÍA": ["TODOS LOS SUBNICHOS (Sector Tech)", "Reparación de Celulares", "Soporte Técnico", "Desarrollo Web", "Venta de Electrónica", "CCTV"],
    "👗 MODA & RETAIL": ["TODOS LOS SUBNICHOS (Sector Moda)", "Tiendas de Ropa", "Zapaterías", "Joyerías", "Supermercados", "Tiendas Deportivas"],
    "🐾 MASCOTAS": ["TODOS LOS SUBNICHOS (Sector Mascotas)", "Veterinarias", "Peluquería Canina", "Tiendas de Mascotas"],
    "🎉 EVENTOS & TURISMO": ["TODOS LOS SUBNICHOS (Sector Turismo)", "Hoteles", "Salones de Eventos", "Fotógrafos", "Agencias de Viajes"],
    "👔 SERVICIOS EMPRESARIALES": ["TODOS LOS SUBNICHOS (Sector B2B)", "Seguridad Privada", "Mensajería", "Mudanzas", "Imprentas"],
}

COUNTRY_CODES = {
    "Colombia": "57", "España": "34", "México": "52", "Argentina": "54",
    "Chile": "56", "Perú": "51", "Ecuador": "593", "Venezuela": "58",
    "Estados Unidos": "1", "Panamá": "507",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run_async(coro):
    """Ejecuta una coroutine en un thread con su propio event loop.
    Propaga el contexto de Streamlit (necesario para st.write, st.toast, etc.)
    y re-lanza cualquier excepción del thread al hilo principal."""
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
    ctx = get_script_run_ctx()
    result = {}
    exc_holder = [None]
    def _target():
        if ctx:
            add_script_run_ctx(threading.current_thread(), ctx)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result['value'] = loop.run_until_complete(coro)
        except Exception as e:
            exc_holder[0] = e
        finally:
            loop.close()
    t = threading.Thread(target=_target)
    t.start()
    t.join()
    if exc_holder[0]:
        raise exc_holder[0]
    return result.get('value')


def get_wa_link(row, country_name):
    tel = str(row['telefono']) if row['telefono'] else ""
    num = "".join(filter(str.isdigit, tel))
    if not num or len(num) < 7:
        return None
    pref = COUNTRY_CODES.get(country_name, "")
    if pref and not num.startswith(pref):
        num = pref + num
    msg = (f"Hola {row['nombre']}, vi tu negocio de {row['tipo']} en Google Maps. "
           f"Tienes una puntuación de {row['rating']} y me gustaría comentarte algo. ¿Hablamos?")
    return f"https://wa.me/{num}?text={urllib.parse.quote(msg)}"


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
init_db()

if 'stop_requested' not in st.session_state: st.session_state.stop_requested = False
if 'total_session'  not in st.session_state: st.session_state.total_session  = 0
if 'last_summary'   not in st.session_state: st.session_state.last_summary   = None
if 'error_msg'      not in st.session_state: st.session_state.error_msg      = None

# ---------------------------------------------------------------------------
# Page config & CSS
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Lead Gen Pro | Elite Dashboard", layout="wide", page_icon="🟢")

if st.session_state.error_msg:
    with st.container():
        st.error(f"🚨 ERROR DETECTADO:\n\n{st.session_state.error_msg}")
        if st.button("️🗑️ CERRAR ERROR"):
            st.session_state.error_msg = None
            st.rerun()

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    .stApp { background-color: #0a0a0a; font-family: 'Inter', sans-serif; color: #ffffff; }
    .neon-text { color: #39FF14; text-shadow: 0 0 8px rgba(57, 255, 20, 0.3); font-weight: 800; }
    [data-testid="stSidebar"] { border-right: 1px solid #222; }
    @media (min-width: 768px) { [data-testid="stSidebar"] { min-width: 350px !important; } }
    [data-testid="stExpander"] { background-color: #161616 !important; border: 1px solid #333 !important; border-radius: 10px !important; margin-bottom: 10px; }
    .stButton>button { width: 100% !important; background: #111111 !important; color: #39FF14 !important; border: 1px solid #39FF14 !important; border-radius: 8px !important; font-weight: 700 !important; padding: 0.5rem; transition: 0.3s; }
    .stButton>button:hover { background: #39FF14 !important; color: #000000 !important; box-shadow: 0 0 15px rgba(57, 255, 20, 0.4) !important; }
    div[data-testid="stMetric"] { background: #161616; border-radius: 12px; padding: 10px !important; border: 1px solid #252525; }
    @media (max-width: 640px) { .stMetric { margin-bottom: 10px; } h1 { font-size: 1.5rem !important; } }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<h2 class='neon-text' style='text-align:center;'>CENTRAL COMMAND <br><small style='color:gray;font-size:12px;'>v2.0.0</small></h2>", unsafe_allow_html=True)
    st.divider()
    modo_escaneo = st.selectbox("MODO DE ESCANEO:", ["🎯 Caza-Sitios (Solo SIN web)", "📈 SEO Audit (Solo CON web)", "🔎 Full Scan (Todo)"])

    with st.expander("🌐 GEOLOCALIZACIÓN", expanded=True):
        pais_sel    = st.selectbox("PAÍS",   sorted(GEO_DATA.keys()))
        depto       = st.selectbox("ESTADO", sorted(GEO_DATA[pais_sel].keys()))
        ciudad_base = st.selectbox("CIUDAD", sorted(GEO_DATA[pais_sel][depto]))
        st.divider()
        tipo_zona = st.radio("COBERTURA:", ["📍 TODA LA CIUDAD", "📍 CENTRO", "⬆️ NORTE", "⬇️ SUR", "🧩 BARRIOS"])
        if tipo_zona == "🧩 BARRIOS":
            barrios = st.text_area("LISTA DE BARRIOS:", "Zona 1").split("\n")
        elif tipo_zona == "📍 TODA LA CIUDAD":
            barrios = [""]
        else:
            barrios = [tipo_zona.replace("📍 ", "").replace("⬆️ ", "").replace("⬇️ ", "")]

    with st.expander("🎯 NICHO Y SECTOR", expanded=True):
        cat       = st.selectbox("CATEGORÍA:", list(NICHOS_DICT.keys()))
        sub       = st.selectbox("NICHO:",     NICHOS_DICT[cat])
        exhaustivo = st.toggle("🚀 EXHAUSTIVO TOTAL (+250)", False)
        nicho = "MODO_EXHAUSTIVO_TOTAL" if exhaustivo else (f"SECTOR_{cat}" if "TODOS" in sub else sub)

    max_res = st.number_input("CAPACIDAD:", 5, 5000, 50)
    infinito = st.toggle("♾️ ILIMITADO", False)
    st.divider()
    c1, c2 = st.columns(2)
    start_btn = c1.button("🚀 INICIAR", type="primary")
    stop_btn  = c2.button("🛑 PARAR")
    if stop_btn:
        st.session_state.stop_requested = True

# ---------------------------------------------------------------------------
# Header & métricas
# ---------------------------------------------------------------------------
st.markdown("<h1 style='font-size: 2.2em; margin-bottom:0;'>LEAD GEN <span class='neon-text'>PRO ELITE</span></h1>", unsafe_allow_html=True)

conn   = sqlite3.connect(DB_PATH)
df_all = pd.read_sql_query("SELECT * FROM leads", conn)
conn.close()

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("🎯 OBJETIVO",  "∞" if infinito else max_res)
m2.metric("🆕 NUEVOS",    len(df_all[df_all['estado'] == 'Nuevo']))
m3.metric("📲 CONTACTO",  len(df_all[df_all['estado'] == 'Contactado']))
m4.metric("🔥 INTERÉS",   len(df_all[df_all['estado'] == 'Interesado']))
m5.metric("💰 CIERRES",   len(df_all[df_all['estado'] == 'Cerrado']))
m6.metric("🌍 TOTAL",     len(df_all))

log_container = st.empty()
if st.session_state.last_summary:
    st.success(f"🔥 Capturados: {st.session_state.last_summary['leads']}")
    st.button("Limpiar", on_click=lambda: setattr(st.session_state, 'last_summary', None))

# ---------------------------------------------------------------------------
# Vista CRM / Mapa
# ---------------------------------------------------------------------------
st.divider()
view_mode = st.radio("💎 VISTA DE TRABAJO:", ["🌓 DIVIDIDA", "🗺️ MAPA FULL", "📝 CRM FULL"], horizontal=True)

with st.expander("🔍 FILTRAR Y CATEGORIZAR CRM", expanded=False):
    f1, f2, f3, f4 = st.columns(4)
    nicho_f  = f1.multiselect("Nicho:",          df_all['nicho'].unique())  if not df_all.empty else []
    tipo_f   = f2.multiselect("Categoría Real:",  df_all['tipo'].unique())   if not df_all.empty else []
    ciudad_f = f3.multiselect("Ciudad:",          df_all['ciudad'].unique()) if not df_all.empty else []
    estado_f = f4.multiselect("Status:", ["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"])
    search_txt = st.text_input("🎯 Buscar por nombre o notas:", placeholder="Escribe para filtrar...")

df_f = df_all.copy()
if nicho_f:    df_f = df_f[df_f['nicho'].isin(nicho_f)]
if tipo_f:     df_f = df_f[df_f['tipo'].isin(tipo_f)]
if ciudad_f:   df_f = df_f[df_f['ciudad'].isin(ciudad_f)]
if estado_f:   df_f = df_f[df_f['estado'].isin(estado_f)]
if search_txt: df_f = df_f[
    df_f['nombre'].str.contains(search_txt, case=False, na=False) |
    df_f['notas'].str.contains(search_txt, case=False, na=False)
]

df_edit = df_f.copy().sort_values(by='id', ascending=False)
df_edit['Chat'] = df_edit.apply(lambda r: get_wa_link(r, pais_sel), axis=1)

_COL_CFG = {
    "estado":   st.column_config.SelectboxColumn("Status", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"]),
    "Chat":     st.column_config.LinkColumn("Chat 📲"),
    "maps_url": st.column_config.LinkColumn("Maps 📍"),
    "web":      st.column_config.LinkColumn("Web"),
    "id":       None,
}

if view_mode == "🌓 DIVIDIDA":
    cl, cr = st.columns([0.45, 0.55])
    with cl:
        st.markdown("#### 🗺️ Mapa Intel")
        map_data = df_f.dropna(subset=['lat', 'lng']).copy()
        if not map_data.empty:
            import folium
            from streamlit_folium import st_folium
            m = folium.Map(location=[map_data["lat"].mean(), map_data["lng"].mean()], zoom_start=12, tiles="CartoDB dark_matter")
            for _, row in map_data.iterrows():
                wa   = get_wa_link(row, pais_sel)
                maps = row.get('maps_url', '#')
                popup = (f"<b>{row['nombre']}</b><br>⭐ {row['rating']} ({row['reseñas']})<br><hr>"
                         f"<a href='{wa}' target='_blank' style='background:#25D366;color:white;padding:5px;"
                         f"display:block;text-align:center;text-decoration:none;border-radius:5px'>WhatsApp 📲</a>"
                         f"<br><a href='{maps}' target='_blank' style='color:#39FF14;text-align:center;display:block;'>Google Maps 📍</a>")
                folium.CircleMarker([row['lat'], row['lng']], radius=10,
                                    color="#39FF14" if row['estado'] == 'Nuevo' else "#FFD700",
                                    fill=True, popup=folium.Popup(popup, max_width=250)).add_to(m)
            st_folium(m, width=None, height=500, key="split_map")
    with cr:
        st.markdown(f"#### 📝 CRM ({len(df_f)} leads)")
        edited_df = st.data_editor(
            df_edit[['id', 'estado', 'notas', 'nombre', 'rating', 'Chat', 'maps_url']],
            column_config=_COL_CFG,
            disabled=["nombre", "rating", "Chat", "maps_url"],
            hide_index=True, width="stretch", height=500,
        )
        if st.button("💾 GUARDAR CRM", type="primary"):
            conn = sqlite3.connect(DB_PATH)
            for _, r in edited_df.iterrows():
                conn.execute("UPDATE leads SET estado=?, notas=? WHERE id=?", (r['estado'], r['notas'], r['id']))
            conn.commit(); conn.close(); st.rerun()

elif view_mode == "🗺️ MAPA FULL":
    map_data = df_f.dropna(subset=['lat', 'lng']).copy()
    if not map_data.empty:
        import folium
        from streamlit_folium import st_folium
        m = folium.Map(location=[map_data["lat"].mean(), map_data["lng"].mean()], zoom_start=13, tiles="CartoDB dark_matter")
        for _, row in map_data.iterrows():
            wa   = get_wa_link(row, pais_sel)
            maps = row.get('maps_url', '#')
            popup = (f"<div style='min-width:220px'><h3>{row['nombre']}</h3>"
                     f"<h2 style='color:#FF8C00'>⭐ {row['rating']}</h2><hr>"
                     f"<a href='{wa}' target='_blank' style='background:#25D366;color:white;padding:10px;"
                     f"display:block;text-align:center;text-decoration:none;border-radius:5px'>WHATSAPP 📲</a>"
                     f"<br><a href='{maps}' target='_blank' style='color:#39FF14;text-align:center;display:block;'>GOOGLE MAPS 📍</a></div>")
            folium.CircleMarker([row['lat'], row['lng']], radius=12,
                                color="#39FF14" if row['estado'] == 'Nuevo' else "#FFD700",
                                fill=True, popup=folium.Popup(popup, max_width=300)).add_to(m)
        st_folium(m, width=None, height=750, key="full_map")

elif view_mode == "📝 CRM FULL":
    edited_df = st.data_editor(
        df_edit[['id', 'estado', 'notas', 'nombre', 'rating', 'reseñas', 'tipo', 'Chat', 'web', 'maps_url', 'nicho', 'fecha', 'ciudad']],
        column_config=_COL_CFG,
        disabled=["nombre", "rating", "reseñas", "tipo", "Chat", "web", "maps_url", "nicho", "fecha", "ciudad"],
        hide_index=True, width="stretch", height=700,
    )
    if st.button("💾 GUARDAR CAMBIOS CRM FULL", type="primary"):
        conn = sqlite3.connect(DB_PATH)
        for _, r in edited_df.iterrows():
            conn.execute("UPDATE leads SET estado=?, notas=? WHERE id=?", (r['estado'], r['notas'], r['id']))
        conn.commit(); conn.close(); st.rerun()

# ---------------------------------------------------------------------------
# Export & Admin
# ---------------------------------------------------------------------------
st.divider()
ec1, ec2 = st.columns([0.7, 0.3])
with ec1:
    st.download_button(
        "📥 DESCARGAR CSV", df_all.to_csv(index=False),
        f"leads_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
        use_container_width=True,
    )
with ec2:
    with st.expander("⚙️ ADMIN DB"):
        if st.button("⚡ COMPACTAR DB", use_container_width=True):
            conn = sqlite3.connect(DB_PATH); conn.execute("VACUUM"); conn.close()
            st.success("Compactada")
        if st.button("🗑️ BORRAR TODO", use_container_width=True):
            if st.session_state.get('confirm_del', False):
                conn = sqlite3.connect(DB_PATH)
                conn.execute("DELETE FROM leads"); conn.commit(); conn.close()
                st.session_state.confirm_del = False; st.rerun()
            else:
                st.warning("¿Seguro?"); st.session_state.confirm_del = True

# ---------------------------------------------------------------------------
# Lanzar scraping
# ---------------------------------------------------------------------------
if start_btn:
    st.session_state.last_summary  = None
    st.session_state.stop_requested = False
    st.session_state.total_session  = 0
    live_c       = log_container.empty()
    progress_bar = st.progress(0, text="🚀 Preparando escaneo...")
    with st.expander("📄 Logs de Prospección", expanded=True):
        try:
            _run_async(main_loop(
                nicho, ciudad_base, pais_sel, barrios,
                max_res, infinito, modo_escaneo,
                st, NICHOS_DICT, live_c, progress_bar,
            ))
        except Exception as e:
            import traceback
            st.session_state.error_msg = f"{e}\n\n{traceback.format_exc()}"
    st.rerun()  # siempre rerun al terminar para mostrar resultados o errores

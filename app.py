import streamlit as st
import asyncio
import pandas as pd
from playwright.async_api import async_playwright
import sqlite3
import datetime
import urllib.parse
import re
from geo_data import GEO_DATA
import time

# --- INITIALIZE STATE ---
if 'stop_requested' not in st.session_state: st.session_state.stop_requested = False
if 'total_session' not in st.session_state: st.session_state.total_session = 0
if 'last_summary' not in st.session_state: st.session_state.last_summary = None

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('leads.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT UNIQUE, telefono TEXT, rating TEXT, reseñas TEXT,
        tipo TEXT, lat REAL, lng REAL, zona TEXT, ciudad TEXT, pais TEXT, 
        nicho TEXT, fecha TEXT, web TEXT, estado TEXT DEFAULT 'Nuevo', notas TEXT)''')
    conn.commit(); conn.close()

def save_lead(lead):
    conn = sqlite3.connect('leads.db', check_same_thread=False)
    try:
        conn.execute('''INSERT OR IGNORE INTO leads (nombre, telefono, rating, reseñas, tipo, lat, lng, zona, ciudad, pais, nicho, fecha, web)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
            (lead['Nombre'], lead['Teléfono'], lead['Rating'], lead['Reseñas'], lead['Tipo'], lead.get('Lat'), lead.get('Lng'), lead['Zona'], lead['Ciudad'], lead['Pais'], lead['Nicho'], lead.get('Fecha', datetime.datetime.now().strftime("%Y-%m-%d")), lead.get('Web')))
        conn.commit()
    finally: conn.close()

init_db()

# --- INTERFACE CONFIG ---
st.set_page_config(page_title="Lead Gen Pro | Elite Suite", layout="wide", page_icon="🟢")

# --- CYBER CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    .stApp { background-color: #0a0a0a; font-family: 'Inter', sans-serif; color: #ffffff; }
    .neon-text { color: #39FF14; text-shadow: 0 0 8px rgba(57, 255, 20, 0.3); font-weight: 800; }
    [data-testid="stSidebar"] { min-width: 320px !important; border-right: 1px solid #222; }
    [data-testid="stExpander"] { background-color: #1a1a1a !important; border: 1px solid #333 !important; border-radius: 10px !important; }
    .stButton>button { width: 100% !important; background: #111111 !important; color: #39FF14 !important; border: 1px solid #39FF14 !important; border-radius: 8px !important; font-weight: 700 !important; }
    .stButton>button:hover { background: #39FF14 !important; color: #000000 !important; box-shadow: 0 0 15px rgba(57, 255, 20, 0.4) !important; }
    div[data-testid="stMetric"] { background: #161616; border-radius: 12px; padding: 10px !important; border: 1px solid #252525; }
    /* Ajuste para pantalla completa */
    .main .block-container { padding-top: 2rem; padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- UTILS ---
def get_wa_link(row):
    p = "".join(filter(str.isdigit, str(row['telefono'])))
    if not p or len(p) < 7: return "#"
    msg = f"Hola {row['nombre']}, vi tu negocio de {row['tipo']} en Google Maps. Tienes una puntuación de {row['rating']} y me gustaría comentarte algo sobre tu presencia online. ¿Hablamos?"
    return f"https://wa.me/{p}?text={urllib.parse.quote(msg)}"

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 class='neon-text' style='text-align:center;'>CENTRAL COMMAND</h2>", unsafe_allow_html=True)
    st.divider()
    modo_escaneo = st.selectbox("MODO DE ESCANEO:", ["🎯 Caza-Sitios (Solo SIN web)", "📈 SEO Audit (Solo CON web)", "🔎 Full Scan (Todo)"])
    
    with st.expander("🌐 GEOLOCALIZACIÓN", expanded=True):
        pais = st.selectbox("PAÍS", sorted(list(GEO_DATA.keys())))
        depto = st.selectbox("ESTADO", sorted(list(GEO_DATA[pais].keys())))
        ciudad_base = st.selectbox("CIUDAD", sorted(GEO_DATA[pais][depto]))
        st.divider()
        tipo_zona = st.radio("COBERTURA:", ["📍 TODA LA CIUDAD", "📍 CENTRO", "⬆️ NORTE", "⬇️ SUR", "🧩 BARRIOS"])
        barrios = st.text_area("LISTA DE BARRIOS:", "Zona Centro").split("\n") if tipo_zona == "🧩 BARRIOS" else ([tipo_zona.replace("📍 ","").replace("⬆️ ","").replace("⬇️ ","")] if tipo_zona != "📍 TODA LA CIUDAD" else [""])
    
    with st.expander("🎯 NICHO Y SECTOR", expanded=True):
        NICHOS_DICT = {
            "🌎 TODOS": ["Todos los Negocios (General)"],
            "🏥 SALUD": ["TODOS LOS SUBNICHOS (Sector Salud)", "Odontólogos", "Clínicas", "Ópticas", "Psicólogos"],
            "🍽️ GASTRO": ["TODOS LOS SUBNICHOS (Sector Gastro)", "Restaurantes", "Cafés", "Pizzerías"],
            "🚗 MOTOR": ["TODOS LOS SUBNICHOS (Sector Motor)", "Talleres", "Repuestos", "Lavaderos"],
            "💄 BELLEZA": ["TODOS LOS SUBNICHOS (Sector Belleza)", "Peluquerías", "Spas", "Estética"],
            "⚖️ PROFESIONAL": ["TODOS LOS SUBNICHOS (Sector Prof)", "Abogados", "Contadores", "Notarías"]
        }
        cat = st.selectbox("CATEGORÍA:", list(NICHOS_DICT.keys()))
        sub = st.selectbox("NICHO:", NICHOS_DICT[cat])
        exhaustivo = st.toggle("🚀 MODO EXHAUSTIVO TOTAL", False)
        nicho = "MODO_EXHAUSTIVO_TOTAL" if exhaustivo else (f"SECTOR_{cat}" if "TODOS LOS" in sub else sub)
    
    max_res = st.number_input("CAPACIDAD:", 5, 5000, 50)
    infinito = st.toggle("♾️ ILIMITADO", False)
    ver_nav = st.checkbox("👁️ VER BROWSER", False)
    
    st.divider()
    c1, c2 = st.columns(2)
    start_btn = c1.button("🚀 INICIAR", type="primary")
    stop_btn = c2.button("🛑 PARAR")
    if stop_btn: st.session_state.stop_requested = True

# --- DASHBOARD HEADER ---
st.markdown("<h1 style='font-size: 2.2em; margin-bottom:0;'>LEAD GEN <span class='neon-text'>PRO ELITE</span></h1>", unsafe_allow_html=True)

conn = sqlite3.connect('leads.db')
df_all = pd.read_sql_query("SELECT * FROM leads", conn)
conn.close()

# Métricas rápidas
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("🎯 OBJETIVO", "∞" if infinito else max_res)
m2.metric("🆕 NUEVOS", len(df_all[df_all['estado'] == 'Nuevo']))
m3.metric("📲 CONTACTO", len(df_all[df_all['estado'] == 'Contactado']))
m4.metric("🔥 INTERÉS", len(df_all[df_all['estado'] == 'Interesado']))
m5.metric("💰 CIERRES", len(df_all[df_all['estado'] == 'Cerrado']))
m6.metric("🌍 TOTAL", len(df_all))

log_container = st.empty()
if st.session_state.last_summary:
    st.success(f"🔥 Operación finalizada: {st.session_state.last_summary['leads']} capturados.")
    if st.button("Cerrar resumen"): st.session_state.last_summary = None; st.rerun()

# --- SELECTOR DE VISTA ---
st.divider()
view_mode = st.radio("💎 SELECCIONAR VISTA DE TRABAJO:", ["🌓 VISTA DIVIDIDA", "🗺️ MAPA TOTAL", "📝 GESTIÓN TOTAL (CRM)"], horizontal=True)

# --- FILTROS GLOBALES DEL CRM ---
with st.expander("🔍 FILTRAR BASE DE DATOS POR CATEGORÍAS", expanded=False):
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        nicho_f = st.multiselect("Nicho de Búsqueda:", options=df_all['nicho'].unique(), default=[])
    with f_col2:
        tipo_f = st.multiselect("Categoría Real (Maps):", options=df_all['tipo'].unique(), default=[])
    with f_col3:
        ciudad_f = st.multiselect("Ciudad:", options=df_all['ciudad'].unique(), default=[])
    with f_col4:
        estado_f = st.multiselect("Status:", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"], default=[])
    
    search_txt = st.text_input("🎯 Buscar por nombre o notas:", placeholder="Escribe para filtrar...")

# Aplicar Filtros
df_filtered = df_all.copy()
if nicho_f: df_filtered = df_filtered[df_filtered['nicho'].isin(nicho_f)]
if tipo_f: df_filtered = df_filtered[df_filtered['tipo'].isin(tipo_f)]
if ciudad_f: df_filtered = df_filtered[df_filtered['ciudad'].isin(ciudad_f)]
if estado_f: df_filtered = df_filtered[df_filtered['estado'].isin(estado_f)]
if search_txt:
    df_filtered = df_filtered[
        df_filtered['nombre'].str.contains(search_txt, case=False, na=False) | 
        df_filtered['notas'].str.contains(search_txt, case=False, na=False)
    ]

# Preparar datos finales
df_edit = df_filtered.copy().sort_values(by='id', ascending=False)
df_edit['Chat'] = df_edit.apply(get_wa_link, axis=1)

# Lógica de Visualización
if view_mode == "🌓 VISTA DIVIDIDA":
    col_l, col_r = st.columns([0.45, 0.55])
    with col_l:
        st.markdown("#### 🗺️ Mapa Intel")
        map_data = df_filtered.dropna(subset=['lat', 'lng']).copy()
        if not map_data.empty:
            import folium
            from streamlit_folium import st_folium
            m = folium.Map(location=[map_data["lat"].mean(), map_data["lng"].mean()], zoom_start=12, tiles="CartoDB dark_matter")
            for _, row in map_data.iterrows():
                colors = {"Nuevo": "#39FF14", "Contactado": "#FFD700", "Interesado": "#FF8C00", "Cerrado": "#00FF00", "Descartado": "#808080"}
                c = colors.get(row['estado'], "#39FF14")
                wa = get_wa_link(row)
                popup = f"<b>{row['nombre']}</b><br>⭐ {row['rating']}<br><a href='{wa}' target='_blank'>Contactar 📲</a>"
                folium.CircleMarker([row['lat'], row['lng']], radius=9, color=c, fill=True, popup=folium.Popup(popup, max_width=250)).add_to(m)
            st_folium(m, width=None, height=500, key="split_map")
    with col_r:
        st.markdown(f"#### 📝 Gestión CRM ({len(df_filtered)} leads)")
        edited_df = st.data_editor(
            df_edit[['id', 'estado', 'notas', 'nombre', 'rating', 'Chat', 'tipo']],
            column_config={"estado": st.column_config.SelectboxColumn("Status", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"]), "Chat": st.column_config.LinkColumn("Chat 📲"), "id": None},
            disabled=["nombre", "rating", "Chat", "tipo"], hide_index=True, width="stretch", height=500
        )
        if st.button("💾 GUARDAR CRM", type="primary"):
            conn = sqlite3.connect('leads.db')
            for _, row in edited_df.iterrows(): conn.execute("UPDATE leads SET estado = ?, notas = ? WHERE id = ?", (row['estado'], row['notas'], row['id']))
            conn.commit(); conn.close(); st.rerun()

elif view_mode == "🗺️ MAPA TOTAL":
    st.markdown(f"#### 🗺️ NAVEGACIÓN COMPLETA ({len(df_filtered)} leads)")
    map_data = df_filtered.dropna(subset=['lat', 'lng']).copy()
    if not map_data.empty:
        import folium
        from streamlit_folium import st_folium
        m = folium.Map(location=[map_data["lat"].mean(), map_data["lng"].mean()], zoom_start=13, tiles="CartoDB dark_matter")
        for _, row in map_data.iterrows():
            colors = {"Nuevo": "#39FF14", "Contactado": "#FFD700", "Interesado": "#FF8C00", "Cerrado": "#00FF00", "Descartado": "#808080"}
            c = colors.get(row['estado'], "#39FF14")
            wa = get_wa_link(row)
            popup = f"<div style='min-width:200px'><b>{row['nombre']}</b><br>⭐ {row['rating']} ({row['reseñas']})<br>🏷️ {row['tipo']}<br><hr><a href='{wa}' target='_blank' style='background:#25D366;color:white;padding:5px;display:block;text-align:center;text-decoration:none;border-radius:5px'>CONTACTAR WHATSAPP</a></div>"
            folium.CircleMarker([row['lat'], row['lng']], radius=12, color=c, fill=True, popup=folium.Popup(popup, max_width=300)).add_to(m)
        st_folium(m, width=None, height=750, key="full_map")

elif view_mode == "📝 GESTIÓN TOTAL (CRM)":
    st.markdown(f"#### 📝 PANEL DE CONTROL ({len(df_filtered)} leads)")
    edited_df = st.data_editor(
        df_edit[['id', 'estado', 'notas', 'nombre', 'rating', 'reseñas', 'tipo', 'Chat', 'web', 'nicho', 'fecha', 'ciudad']],
        column_config={
            "estado": st.column_config.SelectboxColumn("Status", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"]),
            "Chat": st.column_config.LinkColumn("WhatsApp 📲"),
            "web": st.column_config.LinkColumn("Sitio Web"),
            "id": None,
            "rating": st.column_config.TextColumn("⭐"),
            "tipo": st.column_config.TextColumn("Categoría"),
            "fecha": st.column_config.TextColumn("Capturado")
        },
        disabled=["nombre", "rating", "reseñas", "tipo", "Chat", "web", "nicho", "fecha", "ciudad"],
        hide_index=True, width="stretch", height=700
    )
    if st.button("💾 GUARDAR CAMBIOS (VISTA FULL)", type="primary"):
        conn = sqlite3.connect('leads.db')
        for _, row in edited_df.iterrows(): conn.execute("UPDATE leads SET estado = ?, notas = ? WHERE id = ?", (row['estado'], row['notas'], row['id']))
        conn.commit(); conn.close(); st.rerun()

# --- ENGINE ---
async def scrape_zone(context, query, max_results, city, country, nicho_val, infinito, modo_escaneo, log_area, live_counter):
    page = await context.new_page()
    found, audited = 0, 0
    try:
        await page.goto(f"https://www.google.com/maps/search/{urllib.parse.quote(query)}/?hl=es", wait_until="domcontentloaded", timeout=60000)
        try: await page.click('button:has-text("Aceptar")', timeout=3000)
        except: pass
        while (infinito or found < max_results) and not st.session_state.stop_requested:
            items = await page.query_selector_all("a.hfpxzc")
            if audited >= len(items):
                feed = await page.query_selector("div[role='feed']")
                if feed:
                    await feed.evaluate("el => el.scrollBy(0, 1500)"); await asyncio.sleep(2)
                    if len(await page.query_selector_all("a.hfpxzc")) == len(items): break
                    continue
                else: break
            item = items[audited]; audited += 1
            try:
                name = await item.get_attribute("aria-label")
                if not name: continue
                await item.scroll_into_view_if_needed(); await asyncio.sleep(0.5)
                try: await item.click(timeout=3000, force=True)
                except: await item.evaluate("el => el.click()")
                try: await page.wait_for_selector("h1.DUwDvf", timeout=5000)
                except: continue
                
                w_btn = await page.query_selector("a[data-item-id='authority']")
                w_url = await w_btn.get_attribute("href") if w_btn else "Sin sitio web"
                tiene_w = w_url != "Sin sitio web"
                if ("Caza-Sitios" in modo_escaneo and tiene_w) or ("SEO Audit" in modo_escaneo and not tiene_w):
                    log_area.write(f"⏭️ Saltado: {name}"); continue
                
                # GPS
                lat, lng = None, None
                for _ in range(10):
                    m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                    if not m: m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", page.url)
                    if m: lat, lng = float(m.group(1)), float(m.group(2)); break
                    await asyncio.sleep(0.5)
                
                # Data
                p_el = await page.query_selector('button[data-item-id^="phone:tel:"]')
                phone = await p_el.inner_text() if p_el else "N/A"
                
                r_num, rev_num = "N/A", "0"
                r_el = await page.query_selector("span[aria-label*='estrellas']")
                if r_el:
                    m_r = re.search(r"(\d[,\.]\d)", await r_el.get_attribute("aria-label"))
                    if m_r: r_num = f"{m_r.group(1).replace(',', '.')} / 5"
                
                rev_el = await page.query_selector("span[aria-label*='reseñas'], span[aria-label*='opiniones']")
                if rev_el: rev_num = "".join(filter(str.isdigit, await rev_el.get_attribute("aria-label"))) or "0"
                
                tipo_el = await page.query_selector('button[class="Dener"]')
                tipo_txt = await tipo_el.inner_text() if tipo_el else nicho_val

                save_lead({"Nombre": name, "Teléfono": phone, "Rating": r_num, "Reseñas": rev_num, "Tipo": tipo_txt, "Lat": lat, "Lng": lng, "Zona": query, "Ciudad": city, "Pais": country, "Nicho": nicho_val, "Web": w_url})
                found += 1; st.session_state.total_session += 1
                live_counter.markdown(f"<div style='background:#111; border:2px solid #39FF14; border-radius:15px; padding:15px; text-align:center;'><h1 style='margin:0; color:#39FF14;'>{st.session_state.total_session} LEADS</h1></div>", unsafe_allow_html=True)
                log_area.write(f"✅ CAPTURADO: {name}")
            except: continue
    finally: await page.close(); return found

async def main_loop(n, city_base, p, barrios_list, max_r, v, infinito, modo_escaneo, log_area, NICHOS_DICT, live_counter):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not v)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        search_list = []
        if n == "MODO_EXHAUSTIVO_TOTAL":
            for sub in NICHOS_DICT.values(): search_list.extend([x for x in sub if "TODOS LOS" not in x])
            search_list = sorted(list(set(search_list)))
        elif n.startswith("SECTOR_"):
            search_list = [x for x in NICHOS_DICT[n.replace("SECTOR_","")] if "TODOS LOS" not in x]
        else: search_list = [n]
        
        leads_sesion = 0
        for barrio in barrios_list:
            if st.session_state.stop_requested: break
            for nicho_item in search_list:
                if st.session_state.stop_requested: break
                query = f"{nicho_item} en {barrio}, {city_base}, {p}" if barrio else f"{nicho_item} en {city_base}, {p}"
                leads_sesion += await scrape_zone(context, query, max_r, city_base, p, nicho_item, infinito, modo_escaneo, log_area, live_counter)
        await browser.close(); st.session_state.last_summary = {'leads': leads_sesion}

if start_btn:
    st.session_state.last_summary = None; st.session_state.stop_requested = False; st.session_state.total_session = 0
    live_c = log_container.empty()
    with st.expander("📄 Logs de Operación", expanded=False):
        asyncio.run(main_loop(nicho, ciudad_base, pais, barrios, max_res, ver_nav, infinito, modo_escaneo, st, NICHOS_DICT, live_c))
    st.rerun()

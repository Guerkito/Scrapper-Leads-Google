import streamlit as st
import asyncio
import pandas as pd
from playwright.async_api import async_playwright
import sqlite3
import datetime
import urllib.parse
from geo_data import GEO_DATA
import threading
import queue
import time

# --- INITIALIZE STATE ---
if 'running' not in st.session_state:
    st.session_state.running = False
if 'last_summary' not in st.session_state:
    st.session_state.last_summary = None
if 'stop_requested' not in st.session_state:
    st.session_state.stop_requested = False

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('leads.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT UNIQUE, 
        telefono TEXT, 
        rating TEXT, 
        reseñas TEXT,
        tipo TEXT,
        lat REAL,
        lng REAL,
        zona TEXT, 
        ciudad TEXT, 
        pais TEXT, 
        nicho TEXT, 
        fecha TEXT,
        web TEXT,
        estado TEXT DEFAULT 'Nuevo',
        notas TEXT)''')
    
    # Migración de columnas si ya existe la DB
    cols = [
        ("lat", "REAL"), ("lng", "REAL"), ("reseñas", "TEXT"), 
        ("tipo", "TEXT"), ("zona", "TEXT"), ("ciudad", "TEXT"), 
        ("pais", "TEXT"), ("nicho", "TEXT"), ("fecha", "TEXT"),
        ("web", "TEXT"), ("estado", "TEXT"), ("notas", "TEXT")
    ]
    cursor = conn.execute("PRAGMA table_info(leads)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    for col_name, col_type in cols:
        if col_name not in existing_cols:
            try:
                default = " DEFAULT 'Nuevo'" if col_name == "estado" else ""
                conn.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}{default}")
            except: pass
    conn.commit()
    conn.close()

def save_lead(lead):
    conn = sqlite3.connect('leads.db', check_same_thread=False)
    try:
        conn.execute('''INSERT OR IGNORE INTO leads (nombre, telefono, rating, reseñas, tipo, lat, lng, zona, ciudad, pais, nicho, fecha, web)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
            (lead['Nombre'], lead['Teléfono'], lead['Rating'], lead['Reseñas'], lead['Tipo'], lead.get('Lat'), lead.get('Lng'), lead['Zona'], lead['Ciudad'], lead['Pais'], lead['Nicho'], datetime.datetime.now().strftime("%Y-%m-%d"), lead.get('Web')))
        conn.commit()
    finally: conn.close()

init_db()

# --- INTERFACE CONFIG ---
st.set_page_config(page_title="Lead Gen Pro | Suite", layout="wide", page_icon="🟢")

# --- CYBER CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    /* Ajustes Globales */
    .stApp { background-color: #0a0a0a; font-family: 'Inter', sans-serif; color: #ffffff; }
    .neon-text { color: #39FF14; text-shadow: 0 0 8px rgba(57, 255, 20, 0.3); font-weight: 800; }
    
    /* Sidebar y Widgets */
    [data-testid="stSidebar"] { min-width: 320px !important; }
    .stWidgetLabel { white-space: normal !important; word-break: break-word !important; font-size: 0.9rem !important; }
    
    /* Expanders */
    [data-testid="stExpander"] { 
        background-color: #1a1a1a !important; 
        border: 1px solid #333 !important; 
        border-radius: 10px !important; 
        margin-bottom: 10px !important;
        padding: 2px !important;
    }
    
    /* Botones */
    .stButton>button { 
        width: 100% !important;
        background: #111111 !important; 
        color: #39FF14 !important; 
        border: 1px solid #39FF14 !important; 
        border-radius: 8px !important; 
        font-weight: 700 !important; 
        padding: 0.5rem !important;
    }
    .stButton>button:hover { background: #39FF14 !important; color: #000000 !important; box-shadow: 0 0 15px rgba(57, 255, 20, 0.4) !important; }
    
    /* Métricas (Números del CRM y Scanner) */
    div[data-testid="stMetric"] { 
        background: #161616; 
        border-radius: 15px; 
        padding: 10px 15px !important; 
        border: 1px solid #252525;
        overflow: hidden;
    }
    div[data-testid="stMetricValue"] { 
        color: #39FF14 !important; 
        font-weight: 800; 
        font-size: 1.5rem !important; /* Tamaño optimizado para no desbordar */
    }
    div[data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: #888 !important; }

    /* Pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161616 !important;
        border: 1px solid #333 !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 10px 20px !important;
        color: #888 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #39FF14 !important;
        color: #000 !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SCRAPER LOGIC ---
async def scrape_zone(context, query, max_results, city, country, nicho_val, infinito, modo_escaneo):
    page = await context.new_page()
    found = 0
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1: st.markdown("#### 🎯 Objetivo"); obj_text = st.empty(); p_bar = st.progress(0)
    with col_stat2: st.markdown("#### 🔥 Encontrados"); count_text = st.empty()
    with col_stat3: st.markdown("#### 🔍 Auditados"); audit_text = st.empty()
    log_area = st.expander("Registro de actividad", expanded=True)
    
    if infinito: obj_text.markdown("✨ **SIN LÍMITE**")
    else: obj_text.markdown(f"🚩 **{max_results}** resultados")

    try:
        search_url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}/?hl=es"
        log_area.write(f"🌐 Navegando a: {query}...")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        try: await page.click('button:has-text("Aceptar")', timeout=3000)
        except: pass
        
        try: await page.wait_for_selector("a.hfpxzc", timeout=10000)
        except:
            btn = await page.query_selector('button:has-text("Buscar en esta zona")')
            if btn: await btn.click(timeout=3000, force=True); await asyncio.sleep(2)

        audited = 0
        while (infinito or found < max_results) and not st.session_state.get('stop_requested', False):
            items = await page.query_selector_all("a.hfpxzc")
            if not items: break
            
            if audited >= len(items):
                feed = await page.query_selector("div[role='feed']")
                if feed:
                    await feed.evaluate("el => el.scrollBy(0, 1500)")
                    await asyncio.sleep(2)
                    if len(await page.query_selector_all("a.hfpxzc")) == len(items): break
                    continue
                else: break

            item = items[audited]
            audited += 1
            audit_text.metric("Auditados", audited)
            
            try:
                name = await item.get_attribute("aria-label")
                if not name: continue
                await item.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                
                # Súper-clic
                try: await item.click(timeout=3000, force=True)
                except: await item.evaluate("el => el.click()")
                
                try: await page.wait_for_selector("h1.DUwDvf", timeout=5000)
                except: continue

                web_btn = await page.query_selector("a[data-item-id='authority']")
                web_url = await web_btn.get_attribute("href") if web_btn else "Sin sitio web"
                
                # Filtrado con motivo en el log
                tiene_web = web_btn is not None
                es_caza_sitios = "Caza-Sitios" in modo_escaneo
                es_seo_audit = "SEO Audit" in modo_escaneo
                
                if es_caza_sitios and tiene_web:
                    log_area.write(f"⏭️ Saltado: {name} (Ya tiene web)")
                    continue
                elif es_seo_audit and not tiene_web:
                    log_area.write(f"⏭️ Saltado: {name} (No tiene web)")
                    continue
                elif "Full Scan" not in modo_escaneo and not (es_caza_sitios or es_seo_audit):
                    # Por seguridad, si no hay modo claro, no saltar
                    pass

                # Extracción
                tipo_el = await page.query_selector('button[class="Dener"]')
                tipo_txt = await tipo_el.inner_text() if tipo_el else "N/A"
                
                lat, lng = None, None
                for _ in range(5):
                    match = urllib.parse.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                    if not match: match = urllib.parse.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", page.url)
                    import re
                    match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                    if not match: match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", page.url)
                    if match:
                        lat, lng = float(match.group(1)), float(match.group(2))
                        break
                    await asyncio.sleep(0.5)

                phone_el = await page.query_selector('button[data-item-id^="phone:tel:"]')
                phone = await phone_el.inner_text() if phone_el else "N/A"
                
                rating = "N/A"
                rating_el = await page.query_selector("span[aria-label*='estrellas']")
                if rating_el:
                    r_raw = await rating_el.get_attribute("aria-label")
                    m_r = re.search(r"(\d[,\.]\d)", r_raw)
                    if m_r: rating = f"{m_r.group(1).replace(',', '.')} / 5"
                
                save_lead({"Nombre": name, "Teléfono": phone, "Rating": rating, "Reseñas": "S/D", "Tipo": tipo_txt, "Lat": lat, "Lng": lng, "Zona": query, "Ciudad": city, "Pais": country, "Nicho": nicho_val, "Web": web_url})
                found += 1
                count_text.metric("Encontrados", found)
                log_area.write(f"✅ CAPTURADO: {name}")
                
            except: continue
    finally:
        await page.close()
        return found

async def main_loop(n, city_base, p, barrios_list, max_r, v, infinito, modo_escaneo, NICHOS_DICT):
    st.session_state.stop_requested = False
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not v)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        if not v:
            async def block(route):
                if route.request.resource_type in ["image", "media", "font"]: await route.abort()
                else: await route.continue_()
            await context.route("**/*", block)
        
        leads_sesion = 0
        search_list = [n]
        if n == "MODO_EXHAUSTIVO_TOTAL":
            search_list = sorted(list(set([item for sub in NICHOS_DICT.values() for item in sub if item != "Todos los Negocios (General)"])))
        elif n == "Todos los Negocios (General)":
            search_list = ["tiendas", "restaurantes", "oficinas", "servicios", "talleres", "clinicas", "negocios locales"]

        for barrio in barrios_list:
            if st.session_state.stop_requested: break
            for nicho_item in search_list:
                if st.session_state.stop_requested: break
                query = f"{nicho_item} en {barrio}, {city_base}, {p}" if barrio else f"{nicho_item} en {city_base}, {p}"
                st.toast(f"🔎 Analizando: {nicho_item}")
                leads_sesion += await scrape_zone(context, query, max_r, city_base, p, nicho_item, infinito, modo_escaneo)
        
        await browser.close()
        st.session_state.last_summary = {'leads': leads_sesion}

# --- UI TABS ---
tab_scan, tab_crm = st.tabs(["🛰️ LIVE SCANNER", "📊 CRM COMMAND CENTER"])

with st.sidebar:
    st.markdown("<h2 class='neon-text' style='text-align:center;'>CENTRAL COMMAND</h2>", unsafe_allow_html=True)
    st.divider()
    modo_escaneo = st.selectbox("MODO DE ESCANEO:", ["🎯 Caza-Sitios (Solo SIN web)", "📈 SEO Audit (Solo CON web)", "🔎 Full Scan (Todo)"])
    
    with st.expander("🌐 GEOLOCALIZACIÓN", expanded=False):
        pais = st.selectbox("PAÍS", sorted(list(GEO_DATA.keys())))
        depto = st.selectbox("ESTADO", sorted(list(GEO_DATA[pais].keys())))
        ciudad_base = st.selectbox("CIUDAD", sorted(GEO_DATA[pais][depto]))
    
    with st.expander("🎯 NICHO Y SECTOR", expanded=True):
        NICHOS_DICT = {
            "🌎 TODO EL MERCADO": ["Todos los Negocios (General)", "Establecimientos Comerciales"],
            "🏥 SALUD": ["Odontólogos", "Psicólogos", "Fisioterapeutas", "Ópticas", "Clínicas"],
            "🍽️ GASTRONOMÍA": ["Restaurantes", "Cafeterías", "Pizzerías", "Panaderías"],
            "🚗 AUTOMOTRIZ": ["Talleres Mecánicos", "Concesionarios", "Lavado de Autos"],
            "🏠 CONSTRUCCIÓN": ["Inmobiliarias", "Reformas", "Ferreterías"],
            "💄 BELLEZA": ["Peluquerías", "Barberías", "Spas", "Estética"],
            "⚖️ PROFESIONAL": ["Abogados", "Contadores", "Notarías"],
            "🐾 MASCOTAS": ["Veterinarias", "Tiendas de Mascotas"]
        }
        exhaustivo = st.toggle("🚀 MODO EXHAUSTIVO (+150 Nichos)", value=False)
        nicho = "MODO_EXHAUSTIVO_TOTAL" if exhaustivo else st.selectbox("NICHO ESPECÍFICO", NICHOS_DICT[st.selectbox("CATEGORÍA", list(NICHOS_DICT.keys()))])

    max_res = st.number_input("CAPACIDAD POR ZONA", 5, 5000, 50)
    infinito = st.toggle("♾️ EXTRACCIÓN ILIMITADA", False)
    ver_nav = st.checkbox("👁️ MODO OBSERVADOR", False)
    
    st.divider()
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        start_btn = st.button("🚀 INICIAR", type="primary", use_container_width=True)
    with col_btn2:
        stop_btn = st.button("🛑 PARAR", use_container_width=True)

    if start_btn:
        st.session_state.last_summary = None
        st.session_state.stop_requested = False
        asyncio.run(main_loop(nicho, ciudad_base, pais, [""], max_res, ver_nav, infinito, modo_escaneo, NICHOS_DICT))
        st.rerun()
    
    if stop_btn:
        st.session_state.stop_requested = True
        st.warning("🛑 Solicitando parada... el proceso se detendrá en el próximo lead.")

with tab_scan:
    st.markdown("<h1 class='neon-text'>🛰️ SCANNER DE LEADS</h1>", unsafe_allow_html=True)
    if st.session_state.last_summary:
        st.balloons()
        st.success(f"🔥 Operación finalizada: {st.session_state.last_summary['leads']} leads capturados.")
    else:
        st.info("Configura la búsqueda a la izquierda y dale a INICIAR.")

with tab_crm:
    conn = sqlite3.connect('leads.db')
    df = pd.read_sql_query("SELECT * FROM leads ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        st.markdown("<h2 class='neon-text'>📊 CRM COMMAND CENTER</h2>", unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("🆕 NUEVOS", len(df[df['estado'] == 'Nuevo']))
        col2.metric("📲 CONTACTADOS", len(df[df['estado'] == 'Contactado']))
        col3.metric("🔥 INTERESADOS", len(df[df['estado'] == 'Interesado']))
        col4.metric("💰 CERRADOS", len(df[df['estado'] == 'Cerrado']))
        col5.metric("❌ DESCARTADOS", len(df[df['estado'] == 'Descartado']))
        
        st.divider()
        st.markdown("#### 🗺️ Mapa de Inteligencia")
        map_data = df.dropna(subset=['lat', 'lng']).copy()
        if not map_data.empty:
            import folium
            from streamlit_folium import st_folium
            m = folium.Map(location=[map_data["lat"].mean(), map_data["lng"].mean()], zoom_start=12, tiles="CartoDB dark_matter")
            for _, row in map_data.iterrows():
                folium.CircleMarker([row['lat'], row['lng']], radius=8, color="#39FF14", fill=True).add_to(m)
            st_folium(m, width=1200, height=400, key="crm_map")
        
        st.divider()
        st.markdown("#### 📝 Gestión de Prospectos")
        edited_df = st.data_editor(
            df[['id', 'estado', 'notas', 'nombre', 'web', 'telefono', 'rating', 'ciudad', 'nicho']],
            column_config={"estado": st.column_config.SelectboxColumn("Estado", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"]), "web": st.column_config.LinkColumn("Web"), "id": None},
            disabled=["nombre", "web", "telefono", "rating", "ciudad", "nicho"],
            hide_index=True, width="stretch"
        )
        
        if st.button("💾 Guardar Cambios", type="primary"):
            conn = sqlite3.connect('leads.db')
            for _, row in edited_df.iterrows():
                conn.execute("UPDATE leads SET estado = ?, notas = ? WHERE id = ?", (row['estado'], row['notas'], row['id']))
            conn.commit(); conn.close()
            st.success("✅ CRM Actualizado"); time.sleep(1); st.rerun()

        st.divider()
        st.subheader("⚙️ Zona de Peligro")
        if st.button("🗑️ Borrar Toda la Base de Datos"):
            if st.session_state.get('confirm_delete', False):
                conn = sqlite3.connect('leads.db')
                conn.execute("DELETE FROM leads")
                conn.commit(); conn.close()
                st.session_state.confirm_delete = False
                st.success("💥 Base de datos borrada por completo")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("⚠️ ¿Estás seguro? Haz clic de nuevo para confirmar el borrado total.")
                st.session_state.confirm_delete = True
    else:
        st.info("Escanea leads para verlos aquí.")

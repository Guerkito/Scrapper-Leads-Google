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
st.set_page_config(page_title="Lead Gen Pro | Elite Dashboard", layout="wide", page_icon="🟢")

# --- CYBER CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    .stApp { background-color: #0a0a0a; font-family: 'Inter', sans-serif; color: #ffffff; }
    .neon-text { color: #39FF14; text-shadow: 0 0 8px rgba(57, 255, 20, 0.3); font-weight: 800; }
    [data-testid="stSidebar"] { min-width: 320px !important; }
    [data-testid="stExpander"] { background-color: #1a1a1a !important; border: 1px solid #333 !important; border-radius: 10px !important; }
    .stButton>button { width: 100% !important; background: #111111 !important; color: #39FF14 !important; border: 1px solid #39FF14 !important; border-radius: 8px !important; font-weight: 700 !important; }
    .stButton>button:hover { background: #39FF14 !important; color: #000000 !important; box-shadow: 0 0 15px rgba(57, 255, 20, 0.4) !important; }
    div[data-testid="stMetric"] { background: #161616; border-radius: 12px; padding: 10px !important; border: 1px solid #252525; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
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
            "🏥 SALUD & BIENESTAR": ["TODOS LOS SUBNICHOS (Sector Salud)", "Odontólogos", "Psicólogos", "Fisioterapeutas", "Ópticas", "Clínicas Médicas", "Farmacias", "Laboratorios", "Podólogos", "Ginecólogos", "Dermatólogos", "Nutricionistas", "Veterinarias"],
            "🍽️ GASTRONOMÍA": ["TODOS LOS SUBNICHOS (Sector Gastronomía)", "Restaurantes", "Cafeterías", "Pizzerías", "Hamburgueserías", "Panaderías", "Bares", "Sushi", "Comida Vegana", "Heladerías", "Catering"],
            "🚗 AUTOMOTRIZ": ["TODOS LOS SUBNICHOS (Sector Motor)", "Talleres Mecánicos", "Concesionarios", "Lavado de Autos (Spa)", "Venta de Repuestos", "Llantas", "Alquiler de Vehículos", "Centros de Diagnóstico", "Tapicería"],
            "🏠 HOGAR & CONSTRUCCIÓN": ["TODOS LOS SUBNICHOS (Sector Hogar)", "Inmobiliarias", "Reformas", "Pintores", "Cerrajeros", "Electricistas", "Fontaneros", "Carpinterías", "Mueblerías", "Arquitectos", "Constructoras"],
            "💄 BELLEZA & CUIDADO": ["TODOS LOS SUBNICHOS (Sector Belleza)", "Peluquerías", "Barberías", "Spas", "Centros de Uñas", "Estética Facial", "Tatuajes", "Gimnasios", "Crossfit", "Yoga"],
            "⚖️ LEGAL & FINANCIERO": ["TODOS LOS SUBNICHOS (Sector Profesional)", "Abogados", "Contadores", "Notarías", "Asesores Fiscales", "Agencias de Seguros", "Casas de Cambio", "Consultoría Empresarial"],
            "🎓 EDUCACIÓN": ["TODOS LOS SUBNICHOS (Sector Educación)", "Academias de Idiomas", "Jardines Infantiles", "Colegios", "Escuelas de Conducción", "Tutorías", "Academias de Música"],
            "💻 TECNOLOGÍA": ["TODOS LOS SUBNICHOS (Sector Tech)", "Reparación de Celulares", "Soporte Técnico PC", "Agencias de Marketing", "Desarrollo de Software", "Cámaras de Seguridad"],
            "🎉 EVENTOS & TURISMO": ["TODOS LOS SUBNICHOS (Sector Turismo)", "Salones de Eventos", "Fotógrafos", "Agencias de Viajes", "Hoteles", "Discotecas", "Parques de Diversiones"]
        }
        
        cat_sel = st.selectbox("CATEGORÍA:", list(NICHOS_DICT.keys()))
        sub_sel = st.selectbox("NICHO ESPECÍFICO:", NICHOS_DICT[cat_sel])
        
        exhaustivo = st.toggle("🚀 MODO EXHAUSTIVO TOTAL (+150 Nichos)", False)
        
        if exhaustivo:
            nicho = "MODO_EXHAUSTIVO_TOTAL"
            st.info("⚠️ Buscará en TODOS los nichos del sistema uno por uno.")
        elif "TODOS LOS SUBNICHOS" in sub_sel:
            nicho = f"SECTOR_{cat_sel}"
            st.info(f"📂 Barrido completo del sector: {cat_sel}")
        else:
            nicho = sub_sel

    max_res = st.number_input("CAPACIDAD:", 5, 5000, 50)
    infinito = st.toggle("♾️ ILIMITADO", False)
    ver_nav = st.checkbox("👁️ VER BROWSER", False)
    
    st.divider()
    col_b1, col_btn2 = st.columns(2)
    with col_b1: start_btn = st.button("🚀 INICIAR", type="primary")
    with col_btn2: stop_btn = st.button("🛑 PARAR")
    if stop_btn: st.session_state.stop_requested = True

# --- MAIN DASHBOARD ---
st.markdown("<h1 style='font-size: 2.5em; margin-bottom:0;'>LEAD GEN <span class='neon-text'>PRO ELITE</span></h1>", unsafe_allow_html=True)

# 1. UNIFIED METRICS ROW
conn = sqlite3.connect('leads.db')
df_all = pd.read_sql_query("SELECT * FROM leads", conn)
conn.close()

m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
m_col1.metric("🎯 OBJETIVO", "∞" if infinito else max_res)
m_col2.metric("🆕 NUEVOS", len(df_all[df_all['estado'] == 'Nuevo']))
m_col3.metric("📲 CONTACTO", len(df_all[df_all['estado'] == 'Contactado']))
m_col4.metric("🔥 INTERÉS", len(df_all[df_all['estado'] == 'Interesado']))
m_col5.metric("💰 CIERRES", len(df_all[df_all['estado'] == 'Cerrado']))
m_col6.metric("🌍 TOTAL", len(df_all))

# 2. LIVE SCANNER LOGS (Only visible when running or after summary)
if st.session_state.last_summary:
    st.success(f"🔥 Operación finalizada: {st.session_state.last_summary['leads']} capturados.")
    if st.button("Limpiar"): st.session_state.last_summary = None; st.rerun()

log_container = st.empty()

# 3. MAP & CRM SECTION (THE CORE)
st.divider()
col_left, col_right = st.columns([0.45, 0.55])

with col_left:
    st.markdown("#### 🗺️ Mapa de Inteligencia en Tiempo Real")
    map_data = df_all.dropna(subset=['lat', 'lng']).copy()
    if not map_data.empty:
        import folium
        from streamlit_folium import st_folium
        m = folium.Map(location=[map_data["lat"].mean(), map_data["lng"].mean()], zoom_start=12, tiles="CartoDB dark_matter")
        for _, row in map_data.iterrows():
            colors = {"Nuevo": "#39FF14", "Contactado": "#FFD700", "Interesado": "#FF8C00", "Cerrado": "#00FF00", "Descartado": "#808080"}
            c = colors.get(row['estado'], "#39FF14")
            wa = f"https://wa.me/{''.join(filter(str.isdigit, str(row['telefono'])))}"
            popup = f"<b>{row['nombre']}</b><br>Rating: {row['rating']}<br>Status: {row['estado']}<br><a href='{wa}' target='_blank'>WhatsApp 📲</a>"
            folium.CircleMarker([row['lat'], row['lng']], radius=8, color=c, fill=True, fill_opacity=0.8, popup=folium.Popup(popup, max_width=300)).add_to(m)
        st_folium(m, width=None, height=550, key="main_intel_map")
    else: st.info("Mapa esperando datos...")

with col_right:
    st.markdown("#### 📝 Centro de Gestión CRM")
    if not df_all.empty:
        # Link Gen
        df_edit = df_all.copy().sort_values(by='id', ascending=False)
        def get_wa(row):
            p = "".join(filter(str.isdigit, str(row['telefono'])))
            if not p or len(p) < 7: return "N/A"
            msg = f"Hola {row['nombre']}, vi tu perfil en Maps. Tienes {row['rating']} estrellas pero no tienes tu web oficial. ¿Te ayudo?"
            return f"https://wa.me/{p}?text={urllib.parse.quote(msg)}"
        df_edit['Chat'] = df_edit.apply(get_wa, axis=1)

        edited_df = st.data_editor(
            df_edit[['id', 'estado', 'notas', 'nombre', 'web', 'Chat', 'rating', 'ciudad']],
            column_config={
                "estado": st.column_config.SelectboxColumn("Status", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"], width="small"),
                "Chat": st.column_config.LinkColumn("WhatsApp 📲", width="small"),
                "web": st.column_config.LinkColumn("Web", width="small"),
                "id": None
            },
            disabled=["nombre", "web", "Chat", "rating", "ciudad"],
            hide_index=True, width="stretch", height=450
        )
        if st.button("💾 GUARDAR CAMBIOS CRM", type="primary"):
            conn = sqlite3.connect('leads.db')
            for _, row in edited_df.iterrows():
                conn.execute("UPDATE leads SET estado = ?, notas = ? WHERE id = ?", (row['estado'], row['notas'], row['id']))
            conn.commit(); conn.close()
            st.success("¡Datos guardados!"); time.sleep(1); st.rerun()
        
        with st.expander("⚙️ EXPORTAR / BORRAR"):
            st.download_button("📥 Descargar CSV", df_all.to_csv(index=False), "leads_export.csv")
            if st.button("🗑️ RESETEAR BASE DE DATOS"):
                conn = sqlite3.connect('leads.db'); conn.execute("DELETE FROM leads"); conn.commit(); conn.close(); st.rerun()
    else: st.info("CRM esperando leads...")

# --- ENGINE INJECTION ---
async def scrape_zone(context, query, max_results, city, country, nicho_val, infinito, modo_escaneo, log_area):
    page = await context.new_page()
    found = 0
    audited = 0
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
                    log_area.write(f"⏭️ Saltado: {name} (Filtro)"); continue

                lat, lng = None, None
                for _ in range(5):
                    match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                    if not match: match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", page.url)
                    if match: lat, lng = float(match.group(1)), float(match.group(2)); break
                    await asyncio.sleep(0.5)

                p_el = await page.query_selector('button[data-item-id^="phone:tel:"]')
                phone = await p_el.inner_text() if p_el else "N/A"
                
                r_num = "N/A"
                r_el = await page.query_selector("span[aria-label*='estrellas']")
                if r_el:
                    m_r = re.search(r"(\d[,\.]\d)", await r_el.get_attribute("aria-label"))
                    if m_r: r_num = f"{m_r.group(1).replace(',', '.')} / 5"
                
                save_lead({"Nombre": name, "Teléfono": phone, "Rating": r_num, "Reseñas": "S/D", "Tipo": "N/A", "Lat": lat, "Lng": lng, "Zona": query, "Ciudad": city, "Pais": country, "Nicho": nicho_val, "Web": w_url})
                found += 1; log_area.write(f"✅ CAPTURADO: {name}")
            except: continue
    finally: await page.close(); return found

async def main_loop(n, city_base, p, barrios_list, max_r, v, infinito, modo_escaneo, log_area, NICHOS_DICT):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not v)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        leads_sesion = 0
        
        # PREPARAR LISTA DE BÚSQUEDA SEGÚN EL MODO
        if n == "MODO_EXHAUSTIVO_TOTAL":
            search_list = []
            for sub in NICHOS_DICT.values():
                search_list.extend([x for x in sub if "TODOS LOS SUBNICHOS" not in x])
            search_list = sorted(list(set(search_list)))
        elif n.startswith("SECTOR_"):
            sector_name = n.replace("SECTOR_", "")
            search_list = [x for x in NICHOS_DICT[sector_name] if "TODOS LOS SUBNICHOS" not in x]
        elif n == "Todos los Negocios (General)":
            search_list = ["tiendas", "restaurantes", "oficinas", "servicios", "talleres", "clinicas", "negocios locales"]
        else:
            search_list = [n]

        for barrio in barrios_list:
            if st.session_state.stop_requested: break
            for nicho_item in search_list:
                if st.session_state.stop_requested: break
                query = f"{nicho_item} en {barrio}, {city_base}, {p}" if barrio else f"{nicho_item} en {city_base}, {p}"
                st.toast(f"🔎 Analizando: {nicho_item}")
                leads_sesion += await scrape_zone(context, query, max_r, city_base, p, nicho_item, infinito, modo_escaneo, log_area)
        
        await browser.close()
        st.session_state.last_summary = {'leads': leads_sesion}

if start_btn:
    st.session_state.last_summary = None; st.session_state.stop_requested = False
    with log_container.expander("📄 Registro de Actividad en Vivo", expanded=True):
        asyncio.run(main_loop(nicho, ciudad_base, pais, barrios, max_res, ver_nav, infinito, modo_escaneo, st, NICHOS_DICT))
    st.rerun()

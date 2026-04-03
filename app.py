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
st.set_page_config(page_title="Lead Gen Pro | Elite Suite", layout="wide", page_icon="🟢")

# --- CYBER CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    .stApp { background-color: #0a0a0a; font-family: 'Inter', sans-serif; color: #ffffff; }
    .neon-text { color: #39FF14; text-shadow: 0 0 8px rgba(57, 255, 20, 0.3); font-weight: 800; }
    [data-testid="stSidebar"] { min-width: 320px !important; }
    .stWidgetLabel { white-space: normal !important; word-break: break-word !important; font-size: 0.9rem !important; }
    [data-testid="stExpander"] { background-color: #1a1a1a !important; border: 1px solid #333 !important; border-radius: 10px !important; margin-bottom: 10px !important; }
    .stButton>button { width: 100% !important; background: #111111 !important; color: #39FF14 !important; border: 1px solid #39FF14 !important; border-radius: 8px !important; font-weight: 700 !important; }
    .stButton>button:hover { background: #39FF14 !important; color: #000000 !important; box-shadow: 0 0 15px rgba(57, 255, 20, 0.4) !important; }
    div[data-testid="stMetric"] { background: #161616; border-radius: 15px; padding: 10px 15px !important; border: 1px solid #252525; }
    div[data-testid="stMetricValue"] { color: #39FF14 !important; font-weight: 800; font-size: 1.5rem !important; }
    .stTabs [aria-selected="true"] { background-color: #39FF14 !important; color: #000 !important; font-weight: bold !important; border-radius: 8px !important; }
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
                    new_items = await page.query_selector_all("a.hfpxzc")
                    if len(new_items) == len(items): break
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
                
                # Súper-clic resistente
                try: await item.click(timeout=3000, force=True)
                except: await item.evaluate("el => el.click()")
                
                # Esperar a que cargue el panel
                try: await page.wait_for_selector("h1.DUwDvf", timeout=5000)
                except: continue

                # DETECTOR DE WEB MULTICAPA
                web_url = "Sin sitio web"
                web_btn = await page.query_selector("a[data-item-id='authority']")
                if web_btn:
                    web_url = await web_btn.get_attribute("href")
                else:
                    # Intento alternativo por selector de icono de web
                    alt_web = await page.query_selector('a[aria-label*="Sitio web"], a[aria-label*="Website"]')
                    if alt_web: web_url = await alt_web.get_attribute("href")
                
                tiene_web = web_url != "Sin sitio web"
                
                # LÓGICA DE FILTRADO MEJORADA
                if "Full Scan" in modo_escaneo:
                    guardar = True
                elif "Caza-Sitios" in modo_escaneo and not tiene_web:
                    guardar = True
                elif "SEO Audit" in modo_escaneo and tiene_web:
                    guardar = True
                else:
                    guardar = False
                
                if guardar:
                    tipo_el = await page.query_selector('button[class="Dener"]')
                    tipo_txt = await tipo_el.inner_text() if tipo_el else "N/A"
                    
                    lat, lng = None, None
                    for _ in range(5):
                        curr_url = page.url
                        match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", curr_url)
                        if not match: match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", curr_url)
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
                    
                    # Extraer reseñas
                    rev_num = "0"
                    rev_el = await page.query_selector("span[aria-label*='reseñas'], span[aria-label*='opiniones']")
                    if rev_el:
                        rev_raw = await rev_el.get_attribute("aria-label")
                        rev_num = "".join(filter(str.isdigit, rev_raw)) or "0"

                    save_lead({"Nombre": name, "Teléfono": phone, "Rating": rating, "Reseñas": rev_num, "Tipo": tipo_txt, "Lat": lat, "Lng": lng, "Zona": query, "Ciudad": city, "Pais": country, "Nicho": nicho_val, "Web": web_url})
                    found += 1
                    count_text.metric("Encontrados", found)
                    log_area.write(f"✅ CAPTURADO: {name} ({'Web' if tiene_web else 'No Web'})")
                else:
                    motivo = "Ya tiene web" if "Caza-Sitios" in modo_escaneo else "No tiene web"
                    log_area.write(f"⏭️ Saltado: {name} ({motivo})")
                
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
    
    with st.expander("🌐 GEOLOCALIZACIÓN", expanded=True):
        pais = st.selectbox("PAÍS", sorted(list(GEO_DATA.keys())))
        depto = st.selectbox("ESTADO", sorted(list(GEO_DATA[pais].keys())))
        ciudad_base = st.selectbox("CIUDAD", sorted(GEO_DATA[pais][depto]))
        
        st.divider()
        tipo_zona = st.radio("COBERTURA RADIAL:", ["📍 TODA LA CIUDAD", "📍 CENTRO", "⬆️ NORTE", "⬇️ SUR", "⬅️ ESTE", "➡️ OESTE", "🧩 BARRIOS ESPECÍFICOS"])
        if tipo_zona == "🧩 BARRIOS ESPECÍFICOS":
            barrios = st.text_area("LISTA DE BARRIOS:", "Zona 1\nZona 2").split("\n")
        elif tipo_zona == "📍 TODA LA CIUDAD":
            barrios = [""]
        else:
            barrios = [tipo_zona.replace("📍 ", "").replace("⬆️ ", "").replace("⬇️ ", "").replace("⬅️ ", "").replace("➡️ ", "")]
    
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
        if st.button("🚀 INICIAR", type="primary", use_container_width=True):
            st.session_state.last_summary = None
            st.session_state.stop_requested = False
            asyncio.run(main_loop(nicho, ciudad_base, pais, barrios, max_res, ver_nav, infinito, modo_escaneo, NICHOS_DICT))
            st.rerun()
    with col_btn2:
        if st.button("🛑 PARAR", use_container_width=True):
            st.session_state.stop_requested = True
            st.warning("Parando...")

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
                wa_link = f"https://wa.me/{''.join(filter(str.isdigit, str(row['telefono'])))}"
                popup = f"<b>{row['nombre']}</b><br>Rating: {row['rating']}<br><a href='{wa_link}' target='_blank'>WhatsApp 📲</a>"
                folium.CircleMarker([row['lat'], row['lng']], radius=8, color="#39FF14", fill=True, popup=folium.Popup(popup, max_width=300)).add_to(m)
            st_folium(m, width=1200, height=400, key="crm_map")
        
        st.divider()
        st.markdown("#### 📝 Gestión de Prospectos")
        
        # WhatsApp Link Gen para tabla
        df_display = df.copy()
        def get_wa(row):
            phone = "".join(filter(str.isdigit, str(row['telefono'])))
            if not phone or len(phone) < 7: return "N/A"
            msg = f"Hola {row['nombre']}, vi tu perfil en Maps. Tienes {row['rating']} estrellas pero no tienes tu web oficial. ¿Te ayudo?"
            return f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
        df_display['WhatsApp'] = df_display.apply(get_wa, axis=1)

        edited_df = st.data_editor(
            df_display[['id', 'estado', 'notas', 'nombre', 'web', 'WhatsApp', 'telefono', 'rating', 'ciudad', 'nicho']],
            column_config={
                "estado": st.column_config.SelectboxColumn("Estado", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"]),
                "web": st.column_config.LinkColumn("Web"),
                "WhatsApp": st.column_config.LinkColumn("Contactar 📲"),
                "id": None
            },
            disabled=["nombre", "web", "WhatsApp", "telefono", "rating", "ciudad", "nicho"],
            hide_index=True, width="stretch"
        )
        
        if st.button("💾 Guardar Cambios", type="primary"):
            conn = sqlite3.connect('leads.db')
            for _, row in edited_df.iterrows():
                conn.execute("UPDATE leads SET estado = ?, notas = ? WHERE id = ?", (row['estado'], row['notas'], row['id']))
            conn.commit(); conn.close()
            st.success("✅ CRM Actualizado"); time.sleep(1); st.rerun()

        st.divider()
        if st.button("🗑️ Borrar Toda la Base de Datos"):
            if st.session_state.get('confirm_del', False):
                conn = sqlite3.connect('leads.db'); conn.execute("DELETE FROM leads"); conn.commit(); conn.close()
                st.session_state.confirm_del = False; st.rerun()
            else: st.warning("¿Seguro? Dale otra vez."); st.session_state.confirm_del = True
    else: st.info("Escanea leads para verlos aquí.")

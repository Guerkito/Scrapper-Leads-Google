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

# --- PREFIJOS TELEFÓNICOS ---
COUNTRY_CODES = {
    "Colombia": "57", "España": "34", "México": "52", "Argentina": "54", "Chile": "56", 
    "Perú": "51", "Ecuador": "593", "Venezuela": "58", "Estados Unidos": "1", "Panamá": "507"
}

# --- INTERFACE CONFIG ---
st.set_page_config(page_title="Lead Gen Pro | Elite Suite", layout="wide", page_icon="🟢")

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
    </style>
""", unsafe_allow_html=True)

# --- UTILS ---
def get_wa_link(row, country_name):
    num_clean = "".join(filter(str.isdigit, str(row['telefono'])))
    if not num_clean or len(num_clean) < 7: return None
    
    # Añadir prefijo si no lo tiene
    prefix = COUNTRY_CODES.get(country_name, "")
    if prefix and not num_clean.startswith(prefix):
        num_clean = prefix + num_clean
    
    name = row['nombre']
    tipo = row['tipo'] if row['tipo'] != "N/A" else "negocio"
    rating = row['rating']
    
    if rating != "N/A":
        msg = f"Hola {name}, vi tu {tipo} en Google Maps. Tienes una gran puntuación de {rating} y me gustaría ayudarte con tu presencia online. ¿Hablamos?"
    else:
        msg = f"Hola {name}, vi tu {tipo} en Google Maps y me pareció muy interesante. Me gustaría comentarte algo sobre tu visibilidad digital. ¿Hablamos?"
        
    return f"https://wa.me/{num_clean}?text={urllib.parse.quote(msg)}"

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 class='neon-text' style='text-align:center;'>CENTRAL COMMAND</h2>", unsafe_allow_html=True)
    st.divider()
    modo_escaneo = st.selectbox("MODO DE ESCANEO:", ["🎯 Caza-Sitios (Solo SIN web)", "📈 SEO Audit (Solo CON web)", "🔎 Full Scan (Todo)"])
    
    with st.expander("🌐 GEOLOCALIZACIÓN", expanded=True):
        pais_sel = st.selectbox("PAÍS", sorted(list(GEO_DATA.keys())))
        depto = st.selectbox("ESTADO", sorted(list(GEO_DATA[pais_sel].keys())))
        ciudad_base = st.selectbox("CIUDAD", sorted(GEO_DATA[pais_sel][depto]))
        st.divider()
        tipo_zona = st.radio("COBERTURA:", ["📍 TODA LA CIUDAD", "📍 CENTRO", "⬆️ NORTE", "⬇️ SUR", "🧩 BARRIOS"])
        barrios = st.text_area("LISTA DE BARRIOS:", "Zona Centro").split("\n") if tipo_zona == "🧩 BARRIOS" else ([tipo_zona.replace("📍 ","").replace("⬆️ ","").replace("⬇️ ","")] if tipo_zona != "📍 TODA LA CIUDAD" else [""])
    
    with st.expander("🎯 NICHO Y SECTOR", expanded=True):
        NICHOS_DICT = {
            "🌎 TODO EL MERCADO": ["TODOS LOS NEGOCIOS (Barrido Total)", "Empresas locales", "Servicios profesionales", "Establecimientos comerciales"],
            "🏥 SALUD & MEDICINA": [
                "TODOS LOS SUBNICHOS (Sector Salud)", "Odontólogos", "Clínicas Médicas", "Psicólogos", "Fisioterapeutas", "Ópticas", "Dermatólogos", 
                "Ginecólogos", "Pediatras", "Cardiólogos", "Oftalmólogos", "Centros de Estética", "Cirujanos Plásticos", "Laboratorios Clínicos", 
                "Farmacias", "Podólogos", "Nutricionistas", "Ortopedistas", "Urólogos", "Centros de Rehabilitación", "Psiquiatras", "Veterinarias"
            ],
            "🍽️ GASTRONOMÍA & OCIO": [
                "TODOS LOS SUBNICHOS (Sector Gastro)", "Restaurantes", "Cafeterías", "Pizzerías", "Hamburgueserías", "Panaderías", "Pastelerías", 
                "Bares", "Discotecas", "Sushi", "Comida Vegana", "Comida Mexicana", "Comida Italiana", "Steakhouse", "Heladerías", "Catering", 
                "Licorerías", "Food Trucks", "Casas de Banquetes"
            ],
            "🚗 SECTOR AUTOMOTRIZ": [
                "TODOS LOS SUBNICHOS (Sector Motor)", "Talleres Mecánicos", "Concesionarios", "Compraventa de Autos", "Venta de Repuestos", 
                "Llantas y Neumáticos", "Lavado de Autos (Spa)", "Centros de Diagnóstico (CDA)", "Tapicería Automotriz", "Grúas y Asistencia", 
                "Motos (Venta y Taller)", "Montallantas", "Pintura Automotriz", "Alquiler de Vehículos"
            ],
            "🏠 CONSTRUCCIÓN & HOGAR": [
                "TODOS LOS SUBNICHOS (Sector Hogar)", "Inmobiliarias", "Arquitectos", "Constructoras", "Ferreterías", "Materiales de Construcción", 
                "Reformas e Instalaciones", "Pintores", "Electricistas", "Plomeros/Fontaneros", "Carpinterías", "Cerrajeros", "Vidrierías", 
                "Mueblerías", "Decoración de Interiores", "Aire Acondicionado", "Energía Solar", "Sistemas de Seguridad", "Impermeabilizaciones"
            ],
            "💄 BELLEZA & BIENESTAR": [
                "TODOS LOS SUBNICHOS (Sector Belleza)", "Peluquerías", "Barberías", "Spas", "Centros de Uñas (Nails)", "Estética Facial", 
                "Tatuajes (Tattoo Shops)", "Gimnasios", "Centros de CrossFit", "Yoga y Pilates", "Escuelas de Baile", "Masajes Relajantes", 
                "Depilación Láser", "Maquillaje Profesional"
            ],
            "⚖️ PROFESIONALES & LEGAL": [
                "TODOS LOS SUBNICHOS (Sector Profesional)", "Abogados", "Contadores", "Notarías", "Asesores Fiscales", "Agencias de Seguros", 
                "Consultoría de Negocios", "Agencias de Viajes", "Inmobiliarias", "Arquitectos", "Ingenieros Civiles", "Diseñadores Gráficos", 
                "Agencias de Marketing", "Desarrolladores de Software", "Fotógrafos", "Productores Audiovisuales"
            ],
            "🏗️ INDUSTRIAL & TÉCNICO": [
                "TODOS LOS SUBNICHOS (Sector Industrial)", "Fábricas", "Logística y Transporte", "Parques Industriales", "Maquinaria Pesada", 
                "Reciclaje", "Tratamiento de Aguas", "Empresas de Limpieza", "Mantenimiento Industrial", "Control de Plagas", "Embalajes", 
                "Químicos", "Textiles", "Maderas", "Metalúrgicas"
            ],
            "🎓 EDUCACIÓN & FORMACIÓN": [
                "TODOS LOS SUBNICHOS (Sector Educación)", "Colegios Privados", "Jardines Infantiles", "Academias de Idiomas", "Universidades", 
                "Escuelas de Conducción", "Tutorías y Refuerzo", "Academias de Música", "Escuelas de Arte", "Centros de Capacitación", 
                "Librerías", "Bibliotecas"
            ],
            "💻 TECNOLOGÍA & DIGITAL": [
                "TODOS LOS SUBNICHOS (Sector Digital)", "Reparación de Celulares", "Soporte Técnico PC", "Venta de Tecnología", 
                "Tiendas de Electrónica", "Proveedores de Internet", "Desarrollo Web", "Agencias SEO", "Hosting", "Ciberseguridad", 
                "Instalación de CCTV"
            ],
            "👗 MODA & RETAIL": [
                "TODOS LOS SUBNICHOS (Sector Moda)", "Tiendas de Ropa", "Zapaterías", "Joyerías", "Centros Comerciales", "Supermercados", 
                "Tiendas de Regalos", "Floristerías", "Jugueterías", "Ópticas", "Tiendas Deportivas", "Relojerías", "Marroquinería"
            ],
            "🐾 MASCOTAS": [
                "TODOS LOS SUBNICHOS (Sector Mascotas)", "Veterinarias", "Peluquería Canina", "Tiendas de Mascotas", "Entrenadores Caninos", 
                "Guarderías para Perros", "Cementerios de Mascotas", "Acuarios"
            ],
            "🎉 EVENTOS & TURISMO": [
                "TODOS LOS SUBNICHOS (Sector Turismo)", "Hoteles", "Hostales", "Salones de Eventos", "Fotógrafos de Bodas", "Alquiler de Trajes", 
                "Agencias de Viajes", "Guías Turísticos", "Parques de Diversiones", "Museos", "Galerías de Arte"
            ],
            "👔 SERVICIOS EMPRESARIALES": [
                "TODOS LOS SUBNICHOS (Sector B2B)", "Seguridad Privada", "Mensajería y Envíos", "Mudanzas", "Lavanderías Industriales", 
                "Alquiler de Equipos", "Publicidad Exterior", "Imprentas y Litografías", "Papelerías al por mayor", "Suministros de Oficina"
            ],
            "⛪ OTROS": ["Iglesias", "ONGs", "Fundaciones", "Clubes Sociales", "Funerarias", "Centros Comunitarios"]
        }
        
        cat_sel = st.selectbox("CATEGORÍA PRINCIPAL:", list(NICHOS_DICT.keys()))
        sub_sel = st.selectbox("NICHO ESPECÍFICO:", NICHOS_DICT[cat_sel])
        
        exhaustivo = st.toggle("🚀 MODO EXHAUSTIVO TOTAL (+250 Nichos)", False, help="Busca literalmente en CADA sub-nicho de la lista. Es el barrido más potente posible.")
        
        if exhaustivo:
            nicho = "MODO_EXHAUSTIVO_TOTAL"
            st.warning("⚡ MODO EXHAUSTIVO: Se buscará en todos los sectores.")
        elif "TODOS LOS SUBNICHOS" in sub_sel:
            nicho = f"SECTOR_{cat_sel}"
            st.info(f"📂 Barrido completo del sector: {cat_sel}")
        else:
            nicho = sub_sel
    
    max_res = st.number_input("CAPACIDAD:", 5, 5000, 50)
    infinito = st.toggle("♾️ ILIMITADO", False)
    ver_nav = st.checkbox("👁️ VER BROWSER", False)
    
    st.divider()
    c1, c2 = st.columns(2)
    start_btn = c1.button("🚀 INICIAR", type="primary")
    stop_btn = c2.button("🛑 PARAR")
    if stop_btn: st.session_state.stop_requested = True

# --- DASHBOARD ---
st.markdown("<h1 style='font-size: 2.2em; margin-bottom:0;'>LEAD GEN <span class='neon-text'>PRO ELITE</span></h1>", unsafe_allow_html=True)

conn = sqlite3.connect('leads.db')
df_all = pd.read_sql_query("SELECT * FROM leads", conn)
conn.close()

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
    if st.button("Limpiar resumen"): st.session_state.last_summary = None; st.rerun()

st.divider()
view_mode = st.radio("💎 VISTA DE TRABAJO:", ["🌓 DIVIDIDA", "🗺️ MAPA FULL", "📝 CRM FULL"], horizontal=True)

with st.expander("🔍 FILTROS AVANZADOS", expanded=False):
    f1, f2, f3, f4 = st.columns(4)
    nicho_f = f1.multiselect("Nicho:", df_all['nicho'].unique()) if not df_all.empty else []
    tipo_f = f2.multiselect("Tipo:", df_all['tipo'].unique()) if not df_all.empty else []
    ciudad_f = f3.multiselect("Ciudad:", df_all['ciudad'].unique()) if not df_all.empty else []
    estado_f = f4.multiselect("Status:", ["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"])

df_f = df_all.copy()
if nicho_f: df_f = df_f[df_f['nicho'].isin(nicho_f)]
if tipo_f: df_f = df_f[df_f['tipo'].isin(tipo_f)]
if ciudad_f: df_f = df_f[df_f['ciudad'].isin(ciudad_f)]
if estado_f: df_f = df_f[df_f['estado'].isin(estado_f)]

df_edit = df_f.copy().sort_values(by='id', ascending=False)
df_edit['Chat'] = df_edit.apply(lambda r: get_wa_link(r, pais_sel), axis=1)

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
                wa = get_wa_link(row, pais_sel)
                btn_html = f"<a href='{wa}' target='_blank' style='background:#25D366;color:white;padding:8px;display:block;text-align:center;text-decoration:none;border-radius:5px;font-weight:bold;'>WHATSAPP 📲</a>" if wa else "<b style='color:red;display:block;text-align:center;'>NÚMERO INVÁLIDO</b>"
                popup = f"<div style='min-width:180px'><b>{row['nombre']}</b><br>⭐ {row['rating']}<br>🏷️ {row['tipo']}<br><hr>{btn_html}</div>"
                folium.CircleMarker([row['lat'], row['lng']], radius=10, color="#39FF14" if row['estado']=='Nuevo' else "#FFD700", fill=True, popup=folium.Popup(popup, max_width=300)).add_to(m)
            st_folium(m, width=None, height=500, key="split_map")
    with cr:
        st.markdown(f"#### 📝 CRM ({len(df_f)} leads)")
        edited = st.data_editor(df_edit[['id', 'estado', 'notas', 'nombre', 'rating', 'Chat', 'tipo']], column_config={"estado": st.column_config.SelectboxColumn("Status", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"]), "Chat": st.column_config.LinkColumn("Chat 📲"), "id": None}, disabled=["nombre", "rating", "Chat", "tipo"], hide_index=True, width="stretch", height=500)
        if st.button("💾 GUARDAR", type="primary"):
            conn = sqlite3.connect('leads.db')
            for _, r in edited.iterrows(): conn.execute("UPDATE leads SET estado = ?, notas = ? WHERE id = ?", (r['estado'], r['notas'], r['id']))
            conn.commit(); conn.close(); st.rerun()

elif view_mode == "🗺️ MAPA FULL":
    map_data = df_f.dropna(subset=['lat', 'lng']).copy()
    if not map_data.empty:
        import folium
        from streamlit_folium import st_folium
        m = folium.Map(location=[map_data["lat"].mean(), map_data["lng"].mean()], zoom_start=13, tiles="CartoDB dark_matter")
        for _, row in map_data.iterrows():
            wa = get_wa_link(row, pais_sel)
            btn = f"<a href='{wa}' target='_blank' style='background:#25D366;color:white;padding:10px;display:block;text-align:center;text-decoration:none;border-radius:5px;font-weight:bold;'>ENVIAR WHATSAPP 📲</a>" if wa else "<b style='color:red;display:block;text-align:center;'>SIN WHATSAPP ⚠️</b>"
            popup = f"<div style='min-width:220px'><h3 style='margin:0'>{row['nombre']}</h3><h2 style='color:#FF8C00;margin:5px 0'>⭐ {row['rating']}</h2><small>{row['tipo']}</small><br><hr>{btn}</div>"
            folium.CircleMarker([row['lat'], row['lng']], radius=12, color="#39FF14" if row['estado']=='Nuevo' else "#FFD700", fill=True, popup=folium.Popup(popup, max_width=300)).add_to(m)
        st_folium(m, width=None, height=750, key="full_map")

elif view_mode == "📝 CRM FULL":
    edited = st.data_editor(df_edit[['id', 'estado', 'notas', 'nombre', 'rating', 'reseñas', 'tipo', 'Chat', 'web', 'nicho', 'fecha', 'ciudad']], column_config={"estado": st.column_config.SelectboxColumn("Status", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado"]), "Chat": st.column_config.LinkColumn("Chat 📲"), "web": st.column_config.LinkColumn("Web"), "id": None}, disabled=["nombre", "rating", "reseñas", "tipo", "Chat", "web", "nicho", "fecha", "ciudad"], hide_index=True, width="stretch", height=700)
    if st.button("💾 GUARDAR CAMBIOS (VISTA FULL)", type="primary"):
        conn = sqlite3.connect('leads.db')
        for _, row in edited_df.iterrows(): conn.execute("UPDATE leads SET estado = ?, notas = ? WHERE id = ?", (row['estado'], row['notas'], row['id']))
        conn.commit(); conn.close(); st.rerun()

# --- ZONA DE GESTIÓN DE DATOS (AL FINAL) ---
st.divider()
exp_c1, exp_c2 = st.columns([0.7, 0.3])
with exp_c1:
    st.download_button("📥 DESCARGAR BASE DE DATOS COMPLETA (CSV)", df_all.to_csv(index=False, encoding='utf-8-sig'), f"leads_pro_{datetime.datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
with exp_c2:
    with st.expander("⚙️ ADMINISTRAR DB"):
        if st.button("🗑️ BORRAR TODO", use_container_width=True):
            if st.session_state.get('confirm_del', False):
                conn = sqlite3.connect('leads.db')
                conn.execute("DELETE FROM leads")
                conn.commit(); conn.close()
                st.session_state.confirm_del = False
                st.success("Base de datos reseteada.")
                time.sleep(1); st.rerun()
            else:
                st.warning("¿Confirmas el borrado?")
                st.session_state.confirm_del = True

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
                
                lat, lng = None, None
                for _ in range(10):
                    m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                    if not m: m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", page.url)
                    if m: lat, lng = float(m.group(1)), float(m.group(2)); break
                    await asyncio.sleep(0.5)
                
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
                live_counter.markdown(f"<div style='background:#111;border:2px solid #39FF14;border-radius:15px;padding:15px;text-align:center'><h1 style='margin:0;color:#39FF14'>{st.session_state.total_session} LEADS</h1></div>", unsafe_allow_html=True)
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
        for b in barrios_list:
            if st.session_state.stop_requested: break
            for ni in search_list:
                if st.session_state.stop_requested: break
                query = f"{ni} en {b}, {city_base}, {p}" if b else f"{ni} en {city_base}, {p}"
                st.toast(f"🔎: {ni}"); leads_sesion += await scrape_zone(context, query, max_r, city_base, p, ni, infinito, modo_escaneo, log_area, live_counter)
        await browser.close(); st.session_state.last_summary = {'leads': leads_sesion}

if start_btn:
    st.session_state.last_summary = None; st.session_state.stop_requested = False; st.session_state.total_session = 0
    live_c = log_container.empty()
    with st.expander("📄 Logs", expanded=False): asyncio.run(main_loop(nicho, ciudad_base, pais_sel, barrios, max_res, ver_nav, infinito, modo_escaneo, st, NICHOS_DICT, live_c))
    st.rerun()

import streamlit as st
import asyncio
import pandas as pd
from playwright.async_api import async_playwright
import sqlite3
import datetime
import urllib.parse
from geo_data import GEO_DATA

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('leads.db')
    # Crear tabla con todas las columnas si no existe
    conn.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT UNIQUE, 
        telefono TEXT, 
        rating TEXT, 
        tipo TEXT,
        zona TEXT, 
        ciudad TEXT, 
        pais TEXT, 
        nicho TEXT, 
        fecha TEXT)''')
    
    # Asegurar que las columnas nuevas existan (MIGRACIÓN)
    cols = ["tipo", "zona", "ciudad", "pais", "nicho", "fecha"]
    cursor = conn.execute("PRAGMA table_info(leads)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    
    for col in cols:
        if col not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT")
            except: pass
            
    conn.commit()
    conn.close()

def save_lead(lead):
    conn = sqlite3.connect('leads.db')
    try:
        conn.execute('''INSERT OR IGNORE INTO leads (nombre, telefono, rating, tipo, zona, ciudad, pais, nicho, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
            (lead['Nombre'], lead['Teléfono'], lead['Rating'], lead['Tipo'], lead['Zona'], lead['Ciudad'], lead['Pais'], lead['Nicho'], datetime.datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
    finally: conn.close()

init_db()

# --- INTERFACE ---
st.set_page_config(page_title="Lead Gen Pro | Command Center", layout="wide", page_icon="🟢")

# --- CYBER-PRO CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

    /* Fondo Principal y Tipografía */
    .stApp {
        background-color: #0a0a0a;
        font-family: 'Inter', sans-serif;
        color: #ffffff;
    }

    /* Ocultar elementos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Contenedor Bento Box */
    .bento-card {
        background: #161616;
        border: 1px solid #252525;
        border-radius: 24px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    
    .bento-card:hover {
        border-color: #39FF14;
        box-shadow: 0 0 20px rgba(57, 255, 20, 0.1);
        transform: translateY(-2px);
    }

    /* Acentos Verde Neón */
    .neon-text {
        color: #39FF14;
        text-shadow: 0 0 8px rgba(57, 255, 20, 0.3); /* Glow suavizado y elegante */
        font-weight: 800;
    }

    /* Sidebar Título */
    .sidebar-title {
        color: #39FF14;
        font-size: 1.5em;
        font-weight: 800;
        text-align: center;
        letter-spacing: 3px;
        margin-bottom: 20px;
        text-transform: uppercase;
    }

    /* Expanders Sidebar - Dark Mode Premium (Fuerza Bruta) */
    [data-testid="stExpander"], [data-testid="stExpander"] details {
        background-color: #161616 !important;
        border: 1px solid #252525 !important;
        border-radius: 15px !important;
        margin-bottom: 10px !important;
    }

    /* Eliminar fondos blancos en hover, focus y active */
    [data-testid="stExpander"] details summary,
    [data-testid="stExpander"] details summary:hover,
    [data-testid="stExpander"] details summary:focus,
    [data-testid="stExpander"] details summary:active {
        background-color: transparent !important;
        color: white !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    /* Cambiar color de la flecha (chevron) a Verde Neón */
    [data-testid="stExpander"] details summary svg {
        fill: #39FF14 !important;
        filter: drop-shadow(0 0 5px rgba(57, 255, 20, 0.5));
    }

    /* Fondo oscuro para el contenido interno */
    [data-testid="stExpander"] details [data-testid="stExpanderDetails"] {
        background-color: transparent !important;
        padding-top: 10px !important;
    }

    /* Info Box Central - Estilo Terminal */
    div[data-testid="stNotification"] {
        background-color: #111111 !important;
        color: #39FF14 !important;
        border: 1px solid #39FF14 !important;
        border-radius: 15px !important;
        padding: 20px !important;
    }
    
    div[data-testid="stNotification"] svg {
        fill: #39FF14 !important;
    }

    /* Botones Cyberpunk */
    .stButton>button {
        background: #111111 !important;
        color: #39FF14 !important;
        border: 1px solid #39FF14 !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
    }

    .stButton>button:hover {
        background: #39FF14 !important;
        color: #000000 !important;
        box-shadow: 0 0 15px rgba(57, 255, 20, 0.4) !important;
    }

    /* Sidebar Estilizada */
    section[data-testid="stSidebar"] {
        background-color: #0f0f0f !important;
        border-right: 1px solid #252525;
    }

    /* Métricas */
    div[data-testid="stMetric"] {
        background: #161616;
        border-radius: 20px;
        padding: 15px !important;
        border: 1px solid #252525;
    }

    div[data-testid="stMetricValue"] {
        color: #39FF14 !important;
        font-weight: 800;
    }

    /* Resplandores Radiales de Fondo */
    .glow-bg {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: radial-gradient(circle at 10% 10%, rgba(57, 255, 20, 0.05) 0%, transparent 40%),
                    radial-gradient(circle at 90% 90%, rgba(57, 255, 20, 0.05) 0%, transparent 40%);
        pointer-events: none;
        z-index: -1;
    }
    
    /* Input Fields */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #1a1a1a !important;
        color: white !important;
        border: 1px solid #333 !important;
        border-radius: 10px !important;
    }
    </style>
    <div class="glow-bg"></div>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
col_head1, col_head2 = st.columns([0.8, 0.2])
with col_head1:
    st.markdown("<h1 style='font-size: 3.5em; margin-bottom:0;'>LEAD GEN <span class='neon-text'>PRO</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 1.1em; margin-top:-5px;'>INTELIGENCIA GEOGRÁFICA DE ALTA PRECISIÓN</p>", unsafe_allow_html=True)
with col_head2:
    st.markdown("<div style='text-align:right; margin-top:20px;'><span style='background:#111; padding:8px 15px; border-radius:50px; border:1px solid #333; color:#555; font-size:0.8em; font-weight:bold;'>STABLE BUILD v10.1</span></div>", unsafe_allow_html=True)

st.divider()

with st.sidebar:
    st.markdown("<div class='sidebar-title'>CENTRAL COMMAND</div>", unsafe_allow_html=True)
    st.divider()
    
    with st.expander("🌐 GEOLOCALIZACIÓN", expanded=True):
        modo_geo = st.radio("SISTEMA:", ["📍 LISTA DE PRECISIÓN", "🌍 MANUAL GLOBAL"])
        if modo_geo == "📍 LISTA DE PRECISIÓN":
            paises_disponibles = sorted(list(GEO_DATA.keys()))
            pais = st.selectbox("PAÍS", paises_disponibles)
            
            deptos = sorted(list(GEO_DATA[pais].keys()))
            depto = st.selectbox("ESTADO / PROVINCIA", deptos)
            
            ciudades_sug = sorted(GEO_DATA[pais][depto])
            ciudad_sel = st.selectbox("CIUDAD SUGERIDA", ["OTRA CIUDAD (MANUAL)..."] + ciudades_sug)
            
            if ciudad_sel == "OTRA CIUDAD (MANUAL)...":
                # Evitar sugerir Bogotá por defecto fuera de Colombia
                ciudad_base = st.text_input("ESPECIFICAR CIUDAD:", value=f"Ciudad en {depto}")
            else:
                ciudad_base = ciudad_sel
        else:
            pais = st.text_input("PAÍS:", "España")
            ciudad_base = st.text_input("CIUDAD:", "Madrid")
    
    with st.expander("🎯 NICHO Y SECTOR", expanded=True):
        NICHOS_DICT = {
            "🌎 TODO EL MERCADO": ["Todos los Negocios (General)", "Establecimientos Comerciales", "Empresas y Servicios"],
            "🏥 SALUD & BIENESTAR": ["Odontólogos", "Psicólogos", "Fisioterapeutas", "Ópticas", "Centros Médicos", "Ginecólogos", "Dermatólogos", "Cardiólogos", "Centros de Estética", "Nutricionistas", "Podólogos"],
            "🍽️ GASTRONOMÍA": ["Restaurantes", "Cafeterías", "Pizzerías", "Hamburgueserías", "Panaderías", "Bares", "Sushi", "Catering", "Heladerías", "Asaderos de Pollo"],
            "🚗 AUTOMOTRIZ": ["Talleres Mecánicos", "Concesionarios", "Lavado de Autos (Spa)", "Venta de Repuestos", "Llantas/Neumáticos", "Alquiler de Vehículos", "Centros de Diagnóstico (CDA)"],
            "🏠 HOGAR & REAL ESTATE": ["Inmobiliarias", "Reformas Integrales", "Pintores", "Cerrajeros", "Electricistas", "Fontaneros/Plomeros", "Carpinterías", "Vidrierías", "Mueblerías", "Decoración"],
            "💄 BELLEZA": ["Peluquerías", "Barberías", "Spas", "Centros de Uñas (Nails)", "Estética Facial", "Tatuajes (Tattoo Shops)", "Gimnasios/Crossfit", "Centros de Yoga"],
            "⚖️ LEGAL & PROFESIONAL": ["Abogados", "Contadores/Contables", "Notarías", "Arquitectos", "Agencias de Marketing", "Consultorías", "Seguros", "Traducciones"],
            "🐾 MASCOTAS": ["Veterinarias", "Peluquería Canina", "Tiendas de Mascotas", "Entrenadores de Perros", "Hoteles Caninos"],
            "🏗️ CONSTRUCCIÓN & INDUSTRIA": ["Ferreterías", "Materiales de Construcción", "Empresas de Limpieza", "Instaladores de Aire Acondicionado", "Sistemas de Seguridad", "Paneles Solares"],
            "🎓 EDUCACIÓN": ["Academias de Idiomas", "Jardines Infantiles", "Colegios Privados", "Escuelas de Conducción", "Centros de Tutorías", "Escuelas de Baile", "Academias de Música"],
            "👗 MODA & COMERCIO": ["Tiendas de Ropa", "Zapaterías", "Joyarías", "Floristerías", "Ópticas", "Jugueterías", "Regalos/Variedades"],
            "💻 TECNOLOGÍA": ["Reparación de Celulares", "Soporte Técnico PC", "Venta de Electrónica", "Desarrollo de Software", "Diseño Gráfico"],
            "🎉 EVENTOS & OCIO": ["Salones de Eventos", "Fotógrafos", "DJ y Sonido", "Agencias de Viajes", "Hoteles/Hostales", "Discotecas", "Bowling/Bolos"],
            "👔 SERVICIOS PERSONALES": ["Lavanderías/Tintorerías", "Sastrerías", "Mudanzas", "Funerales/Pompas", "Sistemas de Mensajería"]
        }
        cat_nicho = st.selectbox("CATEGORÍA", list(NICHOS_DICT.keys()))
        sub_nicho = st.selectbox("NICHO ESPECÍFICO", NICHOS_DICT[cat_nicho])
        nicho = st.text_input("NICHO CUSTOM:") if st.checkbox("✍️ MODO MANUAL") else sub_nicho

    with st.expander("⚡ PARÁMETROS DE BÚSQUEDA", expanded=True):
        tipo_zona = st.radio("COBERTURA RADIAL:", ["📍 TODA LA CIUDAD", "⬆️ NORTE", "⬇️ SUR", "⬅️ ESTE", "➡️ OESTE", "🧩 BARRIOS ESPECÍFICOS"])
        barrios = st.text_area("LISTA DE BARRIOS:", "Zona Centro").split("\n") if tipo_zona == "🧩 BARRIOS ESPECÍFICOS" else ([""] if tipo_zona == "📍 TODA LA CIUDAD" else [tipo_zona])
        
        modo_infinito = st.toggle("♾️ EXTRACCIÓN ILIMITADA", value=False)
        max_res_per_zone = st.number_input("CAPACIDAD POR ZONA", 5, 5000, 50)
        ver_nav = st.checkbox("👁️ MODO OBSERVADOR (VER BROWSER)", value=False)
    
    st.divider()
    col_start, col_stop = st.columns(2)
    with col_start: start = st.button("🚀 INICIAR", type="primary")
    with col_stop: stop = st.button("🛑 PARAR")

# --- SCRAPER ENGINE ---
async def scrape_zone(context, query, max_results, city, country, nicho_val, infinito):
    page = await context.new_page()
    
    # Placeholders para estadísticas en vivo
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1: 
        st.markdown("#### 🎯 Objetivo")
        obj_text = st.empty()
        p_bar = st.progress(0)
    with col_stat2: st.markdown("#### 🔥 Encontrados"); count_text = st.empty()
    with col_stat3: st.markdown("#### 🔍 Auditados"); audit_text = st.empty()
    
    log_area = st.expander("Registro de actividad en vivo", expanded=True)
    
    if infinito: obj_text.markdown("✨ **SIN LÍMITE** (Buscando todo)")
    else: obj_text.markdown(f"🚩 **{max_results}** resultados")

    try:
        search_url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}/?hl=es"
        log_area.write(f"🌐 Navegando a: {query}...")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        
        # Limpieza inicial
        try: await page.click('button:has-text("Aceptar"), [aria-label="Aceptar todo"]', timeout=5000)
        except: pass

        await page.mouse.move(400, 400); await page.mouse.wheel(0, 500)
        
        try: await page.wait_for_selector("a.hfpxzc", timeout=20000)
        except:
            btn_area = await page.query_selector('button:has-text("Buscar en esta zona")')
            if btn_area: await btn_area.click(); await asyncio.sleep(3)

        found = 0
        audited = 0
        processed_names = set()
        scroll_attempts = 0
        
        while (infinito or found < max_results) and not st.session_state.get('stop_requested', False):
            items = await page.query_selector_all("a.hfpxzc")
            if not items: 
                log_area.write("⚠️ No se encontraron resultados en el mapa.")
                break
            
            # Si ya procesamos todos los elementos visibles, hacemos scroll
            if audited >= len(items):
                feed = await page.query_selector("div[role='feed']")
                if feed:
                    log_area.write("🔄 Cargando más resultados...")
                    await feed.evaluate("el => el.scrollBy(0, 3000)")
                    await asyncio.sleep(3)
                    new_items = await page.query_selector_all("a.hfpxzc")
                    if len(new_items) == len(items):
                        scroll_attempts += 1
                        if scroll_attempts > 3: # Intentar 3 veces antes de rendirse
                            log_area.write("🏁 Fin de los resultados disponibles en esta zona.")
                            break
                        continue
                    else:
                        scroll_attempts = 0 # Reiniciar si cargó nuevos
                        continue
                else:
                    break

            # Procesar el siguiente item por índice
            item = items[audited]
            audited += 1
            
            # Actualizar Dashboard
            audit_text.metric("Total Revisados", audited)
            
            try:
                name = await item.get_attribute("aria-label")
                if not name: continue
                
                await item.scroll_into_view_if_needed()
                await item.click()
                await asyncio.sleep(1.5)
                
                # FILTRO: ¿TIENE WEB? con reintento
                web_btn = None
                for _ in range(2):
                    web_btn = await page.query_selector("a[data-item-id='authority']")
                    if web_btn: break
                    await asyncio.sleep(0.5)
                
                if not web_btn:
                    # EXTRAER CATEGORÍA / TIPO
                    tipo_el = await page.query_selector('button[class="Dener"]')
                    tipo_txt = await tipo_el.inner_text() if tipo_el else "N/A"
                    
                    phone_el = await page.query_selector('button[data-item-id^="phone:tel:"]')
                    phone = await phone_el.inner_text() if phone_el else "N/A"
                    
                    # Extraer y formatear Rating
                    rating_el = await page.query_selector("span[aria-label*='estrellas']")
                    rating_raw = await rating_el.get_attribute("aria-label") if rating_el else "N/A"
                    if rating_raw != "N/A":
                        try:
                            rating_num = rating_raw.split()[0].replace(",", ".")
                            rating = f"{rating_num} / 5"
                        except: rating = "N/A"
                    else: rating = "N/A"
                    
                    save_lead({"Nombre": name, "Teléfono": phone, "Rating": rating, "Tipo": tipo_txt, "Zona": query, "Ciudad": city, "Pais": country, "Nicho": nicho_val})
                    found += 1
                    
                    # Actualizar Dashboard
                    count_text.metric("Leads Calificados", found)
                    if not infinito: p_bar.progress(min(found / max_results, 1.0))
                    else: p_bar.progress(0.99) # Mantener barra casi llena en modo infinito
                    
                    log_area.write(f"✅ **ENCONTRADO:** {name} (Sin web)")
                else:
                    log_area.write(f"⏭️ *Saltado:* {name} (Tiene web)")
            except Exception as e:
                log_area.write(f"⚠️ Error procesando negocio: {str(e)[:50]}")
                continue
            
    except Exception as e:
        st.error(f"❌ Error crítico: {str(e)[:100]}")
    finally:
        await page.close()

async def main_loop(n, city_base, p, barrios_list, max_r, v, infinito):
    st.session_state.stop_requested = False
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not v)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        total_barrios = len(barrios_list)
        for i, barrio in enumerate(barrios_list):
            if st.session_state.get('stop_requested', False):
                break
                
            st.toast(f"📍 Procesando {barrio} ({i+1}/{total_barrios})")
            query = f"{n} en {barrio}, {city_base}, {p}"
            await scrape_zone(context, query, max_r, city_base, p, n, infinito)
            
        await browser.close()
    st.success("🏁 ¡Tarea masiva completada!")

if start:
    asyncio.run(main_loop(nicho, ciudad_base, pais, barrios, max_res_per_zone, ver_nav, modo_infinito))
    st.rerun()

if stop:
    st.session_state.stop_requested = True

# --- CRM DISPLAY ---
conn = sqlite3.connect('leads.db')
df = pd.read_sql_query("SELECT * FROM leads ORDER BY id DESC", conn)
conn.close()

if not df.empty:
    st.divider()
    st.subheader(f"🗄️ Tu Base de Datos Global ({len(df)} prospectos acumulados)")
    
    # --- FILTROS ---
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        nicho_filter = st.multiselect("Filtrar por Nicho:", options=df['nicho'].unique(), default=[])
    with col_f2:
        ciudad_filter = st.multiselect("Filtrar por Ciudad:", options=df['ciudad'].unique(), default=[])
    with col_f3:
        fecha_filter = st.multiselect("Filtrar por Fecha:", options=df['fecha'].unique(), default=[])
    
    # Aplicar filtros
    filtered_df = df.copy()
    if nicho_filter:
        filtered_df = filtered_df[filtered_df['nicho'].isin(nicho_filter)]
    if ciudad_filter:
        filtered_df = filtered_df[filtered_df['ciudad'].isin(ciudad_filter)]
    if fecha_filter:
        filtered_df = filtered_df[filtered_df['fecha'].isin(fecha_filter)]
    
    # --- ESTADÍSTICAS RÁPIDAS ---
    st.markdown("#### 📊 Resumen de Prospectos")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1: st.metric("Total Filtrados", len(filtered_df))
    with col_s2: st.metric("Nichos Diferentes", len(filtered_df['nicho'].unique()))
    with col_s3: st.metric("Ciudades Cubiertas", len(filtered_df['ciudad'].unique()))
    
    # --- TABLA Y DESCARGA ---
    st.dataframe(filtered_df, use_container_width=True)
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            "📥 Descargar Filtrados (CSV)", 
            filtered_df.to_csv(index=False, encoding='utf-8-sig'), 
            f"leads_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
    with col_d2:
        if st.button("🗑️ Limpiar Base de Datos (CUIDADO)"):
            if st.session_state.get('confirm_delete', False):
                conn = sqlite3.connect('leads.db')
                conn.execute("DELETE FROM leads")
                conn.commit()
                conn.close()
                st.session_state.confirm_delete = False
                st.rerun()
            else:
                st.warning("¿Estás seguro? Haz clic de nuevo para confirmar.")
                st.session_state.confirm_delete = True
else:
    st.info("Configura la búsqueda a la izquierda y dale a INICIAR para ver los resultados aquí.")

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
        reseñas TEXT,
        tipo TEXT,
        lat REAL,
        lng REAL,
        zona TEXT, 
        ciudad TEXT, 
        pais TEXT, 
        nicho TEXT, 
        fecha TEXT)''')
    
    # Asegurar que las columnas nuevas existan (MIGRACIÓN)
    cols = [("lat", "REAL"), ("lng", "REAL"), ("reseñas", "TEXT"), ("tipo", "TEXT"), ("zona", "TEXT"), ("ciudad", "TEXT"), ("pais", "TEXT"), ("nicho", "TEXT"), ("fecha", "TEXT")]
    cursor = conn.execute("PRAGMA table_info(leads)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    
    for col_name, col_type in cols:
        if col_name not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")
            except: pass
            
    conn.commit()
    conn.close()

def save_lead(lead):
    conn = sqlite3.connect('leads.db')
    try:
        conn.execute('''INSERT OR IGNORE INTO leads (nombre, telefono, rating, reseñas, tipo, lat, lng, zona, ciudad, pais, nicho, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
            (lead['Nombre'], lead['Teléfono'], lead['Rating'], lead['Reseñas'], lead['Tipo'], lead.get('Lat'), lead.get('Lng'), lead['Zona'], lead['Ciudad'], lead['Pais'], lead['Nicho'], datetime.datetime.now().strftime("%Y-%m-%d")))
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
if 'last_summary' not in st.session_state:
    st.session_state.last_summary = None

col_head1, col_head2 = st.columns([0.8, 0.2])
with col_head1:
    st.markdown("<h1 style='font-size: 3.5em; margin-bottom:0;'>LEAD GEN <span class='neon-text'>PRO</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 1.1em; margin-top:-5px;'>INTELIGENCIA GEOGRÁFICA DE ALTA PRECISIÓN</p>", unsafe_allow_html=True)
with col_head2:
    st.markdown("<div style='text-align:right; margin-top:20px;'><span style='background:#111; padding:8px 15px; border-radius:50px; border:1px solid #333; color:#555; font-size:0.8em; font-weight:bold;'>STABLE BUILD v10.1</span></div>", unsafe_allow_html=True)

# --- DISPLAY LAST SUMMARY ---
if st.session_state.last_summary:
    st.balloons()
    st.markdown(f"""
        <div class='bento-card' style='border-color: #39FF14; text-align: center; margin-top: 20px;'>
            <h2 class='neon-text'>🏁 RESUMEN DE OPERACIÓN FINALIZADA</h2>
            <p style='font-size: 2em; margin-bottom: 0;'><b>{st.session_state.last_summary['leads']}</b></p>
            <p style='color: #888; margin-bottom: 20px;'>Nuevos prospectos calificados capturados</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Cerrar Resumen"):
        st.session_state.last_summary = None
        st.rerun()

st.divider()

with st.sidebar:
    st.markdown("<h2 class='neon-text' style='text-align:center;'>CENTRAL COMMAND</h2>", unsafe_allow_html=True)
    st.divider()

    # --- PERFILES DE ESPECIALISTA (MODO ESTRATEGIA) ---
    with st.expander("👤 PERFIL DE ESPECIALISTA", expanded=True):
        PROFILES = {
            "🌐 Diseñador Web": {
                "desc": "Busca negocios con EXCELENTE reputación (Rating 4.0+) pero SIN WEB oficial. Clientes ideales para diseño de landing pages y sitios corporativos.",
                "sug": "🏥 SALUD, ⚖️ PROFESIONAL o 🏗️ INDUSTRIAL"
            },
            "📸 Fotógrafo / Creador": {
                "desc": "Se enfoca en sectores visuales. Ideal para ofrecer catálogos, menús digitales y tours 360 a negocios con alta rotación.",
                "sug": "🍽️ GASTRONOMÍA, 🎉 EVENTOS o 💄 BELLEZA"
            },
            "📱 Social Media Manager": {
                "desc": "Busca negocios en nichos de 'Estilo de Vida'. Estos clientes necesitan contenido diario y gestión de comunidades.",
                "sug": "💄 BELLEZA, 👗 MODA o 🐾 MASCOTAS"
            },
            "🛡️ Gestor de Reputación": {
                "desc": "Localiza negocios con ratings BAJOS o MEDIOS (< 3.8). Tu servicio es limpiar su imagen y conseguir reseñas positivas.",
                "sug": "🍽️ GASTRONOMÍA, 🏥 SALUD o 🚗 AUTOMOTRIZ"
            },
            "📈 Experto en SEO Local": {
                "desc": "Encuentra negocios en zonas de alta competencia que necesitan posicionarse en el 'Top 3' de Maps para captar llamadas.",
                "sug": "⚖️ PROFESIONAL, 🏗️ INDUSTRIAL o 🏠 HOGAR"
            },
            "🚀 Agencia de Ads (PPC)": {
                "desc": "Apunta a nichos de ALTO TICKET. Estos clientes tienen margen para pagar publicidad en Google y Facebook Ads.",
                "sug": "🏠 INMOBILIARIA, ⚖️ LEGAL o 🏥 SALUD"
            },
            "🤖 Especialista en IA / CRM": {
                "desc": "Busca negocios con MUCHO TRÁFICO de reseñas. Necesitan automatizar su atención al cliente con IA y CRM.",
                "sug": "🍽️ GASTRONOMÍA, 🏥 SALUD o 🎉 EVENTOS"
            }
        }
        perfil_sel = st.selectbox("TU ROL DE VENTAS:", list(PROFILES.keys()))
        st.info(f"💡 **ESTRATEGIA:** {PROFILES[perfil_sel]['desc']}")
        st.caption(f"🎯 **Nichos sugeridos:** {PROFILES[perfil_sel]['sug']}")

    st.divider()
    
    with st.expander("🌐 GEOLOCALIZACIÓN", expanded=False):
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
            "🏥 SALUD & BIENESTAR": ["Odontólogos", "Psicólogos", "Fisioterapeutas", "Ópticas", "Ginecólogos", "Dermatólogos", "Cardiólogos", "Pediatras", "Centros de Estética", "Nutricionistas", "Podólogos", "Farmacias", "Laboratorios Clínicos"],
            "🍽️ GASTRONOMÍA": ["Restaurantes", "Cafeterías", "Pizzerías", "Hamburgueserías", "Panaderías/Pastelerías", "Bares/Pubs", "Sushi", "Comida Mexicana", "Comida Vegana", "Catering", "Heladerías", "Asaderos de Pollo", "Licorerías"],
            "🚗 AUTOMOTRIZ": ["Talleres Mecánicos", "Concesionarios (Venta)", "Lavado de Autos (Spa)", "Venta de Repuestos", "Llantas/Neumáticos", "Alquiler de Vehículos", "Centros de Diagnóstico (CDA)", "Tapicería Automotriz", "Grúas/Asistencia"],
            "🏠 INMOBILIARIA & CONSTRUCCIÓN": ["Inmobiliarias", "Reformas Integrales", "Pintores", "Cerrajeros", "Electricistas", "Fontaneros/Plomeros", "Carpinterías", "Vidrierías", "Mueblerías", "Decoración de Interiores", "Arquitectos", "Constructoras"],
            "💄 BELLEZA & CUIDADO": ["Peluquerías", "Barberías", "Spas", "Centros de Uñas (Nails)", "Estética Facial", "Tatuajes (Tattoo Shops)", "Gimnasios", "Crossfit", "Yoga/Pilates", "Escuelas de Baile"],
            "⚖️ LEGAL & FINANCIERO": ["Abogados", "Contadores/Contables", "Notarías", "Asesores Fiscales", "Agencias de Seguros", "Casas de Cambio", "Consultoría Empresarial"],
            "🐾 MASCOTAS": ["Veterinarias", "Peluquería Canina", "Tiendas de Mascotas", "Entrenadores", "Hoteles Caninos", "Cementerios de Mascotas"],
            "🏗️ INDUSTRIAL & TÉCNICO": ["Ferreterías", "Materiales de Construcción", "Empresas de Limpieza", "Aire Acondicionado", "Sistemas de Seguridad", "Paneles Solares", "Control de Plagas", "Mantenimiento Industrial"],
            "🎓 EDUCACIÓN & CULTURA": ["Academias de Idiomas", "Jardines Infantiles", "Colegios Privados", "Escuelas de Conducción", "Centros de Tutorías", "Academias de Música", "Librerías", "Museos/Galerías"],
            "👗 MODA & RETAIL": ["Tiendas de Ropa", "Zapaterías", "Joyarías", "Floristerías", "Jugueterías", "Regalos/Variedades", "Centros Comerciales", "Supermercados"],
            "💻 TECNOLOGÍA & DIGITAL": ["Reparación de Celulares", "Soporte Técnico PC", "Venta de Electrónica", "Agencias de Marketing Digital", "Desarrollo de Software", "Diseño Gráfico", "Instalación de Cámaras/CCTV"],
            "🎉 EVENTOS & TURISMO": ["Salones de Eventos", "Fotógrafos", "DJ y Sonido", "Agencias de Viajes", "Hoteles/Hostales", "Discotecas", "Bowling/Bolos", "Parques de Diversiones"],
            "👔 LOGÍSTICA & SERVICIOS": ["Mensajería/Currier", "Mudanzas", "Lavanderías", "Sastrerías", "Funerales", "Seguridad Privada", "Alquiler de Equipos"],
            "🌱 ENERGÍA & AMBIENTE": ["Instalaciones Eléctricas", "Gestión de Residuos", "Viveros/Paisajismo", "Tratamiento de Agua"]
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
        
        # Cargar nombres ya existentes para evitar re-auditar
        conn = sqlite3.connect('leads.db')
        cursor = conn.execute("SELECT nombre FROM leads")
        processed_names = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        while (infinito or found < max_results) and not st.session_state.get('stop_requested', False):
            # Intentar pulsar "Buscar en esta zona" si aparece para expandir resultados
            try:
                search_area_btn = await page.query_selector('button:has-text("Buscar en esta zona"), button:has-text("Search this area")')
                if search_area_btn:
                    await search_area_btn.click()
                    await asyncio.sleep(2)
            except: pass

            items = await page.query_selector_all("a.hfpxzc")
            if not items: 
                log_area.write("⚠️ No se encontraron resultados iniciales. Reintentando...")
                await asyncio.sleep(3)
                continue
            
            # Si ya procesamos todos los elementos visibles, hacemos scroll profundo
            if audited >= len(items):
                feed = await page.query_selector("div[role='feed']")
                if feed:
                    log_area.write("🔄 Scroll profundo: Cargando más resultados...")
                    # Scroll por etapas para engañar al algoritmo de Google
                    for _ in range(3):
                        await feed.evaluate("el => el.scrollBy(0, 1500)")
                        await asyncio.sleep(1)
                    
                    await asyncio.sleep(2) # Espera final de carga
                    new_items = await page.query_selector_all("a.hfpxzc")
                    
                    if len(new_items) == len(items):
                        scroll_attempts += 1
                        if scroll_attempts > 5: # Más intentos para zonas difíciles
                            log_area.write("🏁 Se ha alcanzado el límite de resultados de Google para esta zona.")
                            break
                        continue
                    else:
                        scroll_attempts = 0
                        continue
                else: break

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

                    # EXTRAER COORDENADAS (De la URL)
                    lat, lng = None, None
                    try:
                        url = page.url
                        import re
                        match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
                        if match:
                            lat, lng = float(match.group(1)), float(match.group(2))
                    except: pass

                    phone_el = await page.query_selector('button[data-item-id^="phone:tel:"]')

                    phone = await phone_el.inner_text() if phone_el else "N/A"
                    
                    # Extraer Rating y Reseñas
                    rating_el = await page.query_selector("span[aria-label*='estrellas']")
                    rating_raw = await rating_el.get_attribute("aria-label") if rating_el else "N/A"
                    
                    reviews_el = await page.query_selector("span[aria-label*='reseñas'], span[aria-label*='opiniones']")
                    reviews_raw = await reviews_el.get_attribute("aria-label") if reviews_el else "0"
                    
                    if rating_raw != "N/A":
                        try:
                            rating_num = rating_raw.split()[0].replace(",", ".")
                            rating = f"{rating_num} / 5"
                        except: rating = "N/A"
                    else: rating = "N/A"
                    
                    try: reviews = "".join(filter(str.isdigit, reviews_raw)) or "0"
                    except: reviews = "0"
                    
                    save_lead({"Nombre": name, "Teléfono": phone, "Rating": rating, "Reseñas": reviews, "Tipo": tipo_txt, "Lat": lat, "Lng": lng, "Zona": query, "Ciudad": city, "Pais": country, "Nicho": nicho_val})
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
        return found

async def main_loop(n, city_base, p, barrios_list, max_r, v, infinito):
    st.session_state.stop_requested = False
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not v)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # LISTA DE CATEGORÍAS PARA BARRIDO TOTAL (Deep Scan)
        # Extraemos todos los sub-nichos del diccionario global para no dejar ni uno fuera
        DEEP_SCAN_LIST = []
        for sub_list in NICHOS_DICT.values():
            DEEP_SCAN_LIST.extend(sub_list)
        
        # Eliminar duplicados y el ítem de "Todo el mercado"
        DEEP_SCAN_LIST = sorted(list(set(DEEP_SCAN_LIST)))
        if "Todos los Negocios (General)" in DEEP_SCAN_LIST: DEEP_SCAN_LIST.remove("Todos los Negocios (General)")

        total_barrios = len(barrios_list)
        leads_sesion = 0
        
        for i, barrio in enumerate(barrios_list):
            if st.session_state.get('stop_requested', False):
                st.warning(f"🛑 Detenido. Zonas procesadas: {i}/{total_barrios}")
                break
            
            # DETERMINAR QUÉ BUSCAR
            if n == "Todos los Negocios (General)" and infinito:
                # MODO DEEP SCAN: Iterar por TODOS los sub-nichos del sistema
                search_list = DEEP_SCAN_LIST
                st.toast(f"🚀 INICIANDO DEEP SCAN EN {barrio or city_base}")
            elif n == "Todos los Negocios (General)":
                # MODO BARRIDO RÁPIDO: Solo categorías principales
                search_list = ["odontologos", "restaurantes", "talleres", "inmobiliarias", "peluquerias", "abogados", "tiendas", "hoteles", "colegios"]
            else:
                search_list = [n]

            for search_nicho in search_list:
                if st.session_state.get('stop_requested', False): break
                
                query = f"{search_nicho} en {barrio}, {city_base}, {p}" if barrio else f"{search_nicho} en {city_base}, {p}"

                st.toast(f"🔎 Analizando: {search_nicho}")
                encontrados_zona = await scrape_zone(context, query, max_r, city_base, p, n, infinito)
                leads_sesion += encontrados_zona
            
            if leads_sesion > 0:
                st.toast(f"✅ ¡Zona completada! +{leads_sesion} leads totales", icon="🔥")
            
        await browser.close()
        
        # Guardar en memoria de sesión persistente
        st.session_state.last_summary = {'leads': leads_sesion}

if start:
    st.session_state.last_summary = None # Limpiar resumen anterior
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
    
    # --- MAPA TÁCTICO ---
    map_data = filtered_df.dropna(subset=['lat', 'lng']).copy()
    if not map_data.empty:
        st.markdown("#### 🗺️ Mapa Táctico de Prospectos")
        # Renombrar lng a lon para que Streamlit lo reconozca
        map_data = map_data.rename(columns={'lat': 'lat', 'lng': 'lon'})
        st.map(map_data[['lat', 'lon']], size=20, color="#39FF14")

    # --- TABLA Y DESCARGA ---
    # Calcular Lead Score y WhatsApp Link
    display_df = filtered_df.copy()
    
    def calculate_wa(row):
        phone = "".join(filter(str.isdigit, str(row['telefono'])))
        if not phone or len(phone) < 7: return "N/A"
        msg = f"Hola {row['nombre']}, vi tu negocio en Google Maps y me encantó la puntuación de {row['rating']} que tienes. Noté que no tienes sitio web oficial y me gustaría ayudarte con eso. ¿Te interesaría?"
        msg_encoded = urllib.parse.quote(msg)
        return f"https://wa.me/{phone}?text={msg_encoded}"

    def get_status(row):
        try:
            r_num = float(row['rating'].split("/")[0])
            rev_num = int(row['reseñas'])
            if r_num >= 4.0 and rev_num >= 20: return "🔥 ORO"
            if r_num >= 3.5: return "✅ Bueno"
            return "⚪ Frío"
        except: return "⚪ S/D"

    display_df['Status'] = display_df.apply(get_status, axis=1)
    display_df['WhatsApp'] = display_df.apply(calculate_wa, axis=1)
    
    # Reordenar columnas para que WhatsApp y Status estén al principio
    cols = ['Status', 'nombre', 'WhatsApp', 'telefono', 'rating', 'reseñas', 'tipo', 'ciudad', 'nicho', 'fecha']
    display_df = display_df[cols]

    st.dataframe(
        display_df, 
        use_container_width=True,
        column_config={
            "WhatsApp": st.column_config.LinkColumn("WhatsApp 📲", help="Clic para contactar"),
            "Status": st.column_config.TextColumn("Calificación 🏆", help="Prioridad del Lead")
        }
    )
    
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

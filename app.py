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
st.set_page_config(page_title="Lead Gen Pro v10", layout="wide")
st.title("⚡ Lead Gen Pro - Dashboard en Vivo v10")

with st.sidebar:
    st.header("⚙️ Configuración")
    
    # 1. País
    paises_disponibles = sorted(list(GEO_DATA.keys()))
    pais = st.selectbox("País", paises_disponibles)
    
    # 2. Departamento / Estado
    deptos = sorted(list(GEO_DATA[pais].keys()))
    depto = st.selectbox("Departamento / Estado", deptos)
    
    # 3. Ciudad Base (Sugerencias)
    ciudades_sug = sorted(GEO_DATA[pais][depto])
    ciudad_sel = st.selectbox("Ciudad Principal (Sugerida)", ["Otra..."] + ciudades_sug)
    
    if ciudad_sel == "Otra...":
        ciudad_base = st.text_input("Escribe la Ciudad manualmente:")
    else:
        ciudad_base = ciudad_sel
    
    # 4. Nichos y Subnichos
    st.subheader("🎯 Nichos y Especialidades")
    NICHOS_DICT = {
        "🏥 Salud": ["Odontólogos", "Psicólogos", "Fisioterapeutas", "Ópticas", "Ginecólogos", "Dermatólogos", "Centros Médicos"],
        "🍽️ Gastronomía": ["Restaurantes", "Cafeterías", "Pizzerías", "Hamburgueserías", "Panaderías", "Bares", "Sushi"],
        "🚗 Motor": ["Talleres Mecánicos", "Concesionarios", "Lavado de Autos", "Repuestos de Vehículos", "Llantas/Neumáticos"],
        "🏠 Hogar e Inmuebles": ["Inmobiliarias", "Reformas Integrales", "Pintores", "Cerrajeros", "Electricistas", "Fontaneros/Plomeros"],
        "💄 Belleza y Estética": ["Peluquerías", "Barberías", "Centros de Uñas (Nails)", "Spas", "Centros de Estética"],
        "⚖️ Servicios Profesionales": ["Abogados", "Contadores/Contables", "Notarías", "Arquitectos", "Agencias de Marketing"],
        "🐾 Mascotas": ["Veterinarias", "Peluquería Canina", "Tiendas de Mascotas", "Entrenadores de Perros"],
        "🏗️ Construcción": ["Ferreterías", "Materiales de Construcción", "Carpinterías", "Vidrierías"],
        "🎓 Educación": ["Academias de Idiomas", "Jardines Infantiles", "Escuelas de Conducción", "Gimnasios/Crossfit"],
        "✨ Otros": ["Floristerías", "Tiendas de Ropa", "Joyarías", "Mueblerías"]
    }
    
    cat_nicho = st.selectbox("Categoría de Negocio", list(NICHOS_DICT.keys()))
    sub_nicho = st.selectbox("Especialidad (Sub-nicho)", NICHOS_DICT[cat_nicho])
    
    # Opción de personalización manual
    custom_nicho = st.checkbox("✍️ Escribir nicho personalizado manualmente")
    if custom_nicho:
        nicho = st.text_input("Escribe el nicho exactamente como quieres buscarlo:")
    else:
        nicho = sub_nicho
    
    st.divider()
    st.subheader("📍 ¿Dónde buscar?")
    tipo_zona = st.radio("Selecciona cobertura:", ["Toda la ciudad", "Sur", "Norte", "Este", "Oeste", "Zonas Personalizadas"])
    
    if tipo_zona == "Zonas Personalizadas":
        st.caption("Escribe un barrio por línea")
        barrios_input = st.text_area("Lista de Barrios:", "Zona Centro\nBarrio Alto", height=150)
        barrios = [b.strip() for b in barrios_input.split("\n") if b.strip()]
    elif tipo_zona == "Toda la ciudad":
        barrios = [""] # Búsqueda general
    else:
        barrios = [tipo_zona] # El nombre de la zona (Sur, Norte, etc)
    
    st.divider()
    col_inf1, col_inf2 = st.columns(2)
    with col_inf1: modo_infinito = st.toggle("♾️ Modo Infinito", value=False, help="Ignora el límite y busca hasta que des a PARAR")
    with col_inf2: max_res_per_zone = st.number_input("Resultados por barrio", 5, 1000, 20)
    
    ver_nav = st.checkbox("👁️ Ver navegador", value=False)
    
    col1, col2 = st.columns(2)
    with col1: start = st.button("🚀 INICIAR")
    with col2: stop = st.button("🛑 PARAR")

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

import streamlit as st
import asyncio
import threading
import datetime
import urllib.parse
import sqlite3
import pandas as pd
import altair as alt
import requests
import time
import random
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
from geo_data import GEO_DATA
from db import DB_PATH, init_db
from scraper import main_loop
from city_coords import generate_grid, CITY_COORDS
from geocerca import generate_grid_in_feature, feature_centroid

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

# Términos alternativos por nicho para ampliar la cobertura de búsqueda
NICHO_SYNONYMS = {
    "Odontólogos":            ["Dentistas", "Clínica dental"],
    "Clínicas Médicas":       ["Centro médico", "Consultorio médico"],
    "Psicólogos":             ["Psicología", "Terapeuta"],
    "Fisioterapeutas":        ["Fisioterapia", "Rehabilitación física"],
    "Ópticas":                ["Optometría", "Óptico"],
    "Dermatólogos":           ["Dermatología", "Clínica estética"],
    "Ginecólogos":            ["Ginecología"],
    "Pediatras":              ["Pediatría", "Médico pediatra"],
    "Veterinarias":           ["Veterinario", "Clínica veterinaria"],
    "Restaurantes":           ["Restaurant", "Comida", "Almuerzo"],
    "Cafeterías":             ["Café", "Coffee shop"],
    "Pizzerías":              ["Pizza", "Pizzería"],
    "Hamburgueserías":        ["Hamburguesas", "Burger"],
    "Panaderías":             ["Pastelería", "Repostería"],
    "Bares":                  ["Bar", "Taberna", "Cantina"],
    "Sushi":                  ["Japonés", "Sushi bar"],
    "Comida Vegana":          ["Restaurante vegano", "Comida saludable"],
    "Talleres Mecánicos":     ["Mecánica automotriz", "Taller de carros"],
    "Concesionarios":         ["Venta de carros", "Agencia de autos"],
    "Venta de Repuestos":     ["Repuestos", "Autopartes"],
    "Lavado de Autos":        ["Car wash", "Autolavado", "Lavadero"],
    "Motos":                  ["Motocicletas", "Venta de motos"],
    "Inmobiliarias":          ["Bienes raíces", "Finca raíz", "Arriendos"],
    "Constructoras":          ["Construcción", "Contratista"],
    "Ferreterías":            ["Materiales de construcción"],
    "Reformas":               ["Remodelaciones", "Acabados"],
    "Cerrajeros":             ["Cerrajería"],
    "Mueblerías":             ["Muebles"],
    "Peluquerías":            ["Salón de belleza", "Estilista"],
    "Barberías":              ["Barbería", "Barbero"],
    "Spas":                   ["Centro de bienestar", "Masajes"],
    "Centros de Uñas":        ["Manicure", "Uñas acrílicas"],
    "Gimnasios":              ["Gym", "Fitness", "Centro deportivo"],
    "Yoga":                   ["Yoga studio", "Pilates"],
    "Tatuajes":               ["Estudio de tatuajes", "Piercing"],
    "Abogados":               ["Bufete", "Estudio jurídico"],
    "Contadores":             ["Contador público", "Asesor contable"],
    "Notarías":               ["Notario"],
    "Agencias de Seguros":    ["Seguros", "Aseguradora"],
    "Agencias de Marketing":  ["Marketing digital", "Publicidad"],
    "Logística":              ["Transporte", "Courier"],
    "Mantenimiento":          ["Plomería", "Electricista", "Servicios del hogar"],
    "Control de Plagas":      ["Fumigación"],
    "Colegios":               ["Institución educativa", "Escuela"],
    "Jardines Infantiles":    ["Preescolar", "Guardería"],
    "Academias de Idiomas":   ["Clases de inglés", "Escuela de idiomas"],
    "Escuelas de Conducción": ["Autoescuela", "Clases de manejo"],
    "Reparación de Celulares":["Servicio técnico celulares"],
    "Soporte Técnico":        ["Técnico de sistemas", "Servicio técnico PC"],
    "Desarrollo Web":         ["Páginas web", "Diseño web"],
    "CCTV":                   ["Cámaras de seguridad"],
    "Tiendas de Ropa":        ["Boutique", "Ropa"],
    "Zapaterías":             ["Calzado"],
    "Joyerías":               ["Bisutería"],
    "Tiendas Deportivas":     ["Artículos deportivos"],
    "Peluquería Canina":      ["Dog grooming", "Peluquería para perros"],
    "Tiendas de Mascotas":    ["Pet shop"],
    "Hoteles":                ["Hospedaje", "Hostal"],
    "Salones de Eventos":     ["Salón de fiestas"],
    "Fotógrafos":             ["Estudio fotográfico"],
    "Agencias de Viajes":     ["Tour operador", "Viajes"],
    "Seguridad Privada":      ["Vigilancia"],
    "Mensajería":             ["Delivery", "Paquetería"],
    "Mudanzas":               ["Fletes"],
    "Imprentas":              ["Litografía", "Papelería"],
    "Empresas locales":       ["Negocios locales"],
    "Servicios profesionales":["Profesionales independientes"],
}

_NIVEL_CONFIG = {
    "⚡ Rápido  (1 punto)":     {"grid_n": 1,  "label": "1 punto"},
    "🏙️ Normal  (9 puntos)":    {"grid_n": 3,  "label": "9 GPS"},
    "🗺️ Amplio  (25 puntos)":   {"grid_n": 5,  "label": "25 GPS"},
    "🌍 Máximo  (49 puntos)":   {"grid_n": 7,  "label": "49 GPS"},
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


# ---------------------------------------------------------------------------
# Estado compartido de campaña (objeto a nivel de módulo, accesible desde hilos)
# ---------------------------------------------------------------------------
class _CampState:
    def __init__(self):
        self.running   = False
        self.logs      = []   # lista de (nivel, mensaje)
        self.progress  = 0.0
        self.countdown = 0
        self.stop      = False

    def reset(self):
        self.running   = True
        self.logs      = []
        self.progress  = 0.0
        self.countdown = 0
        self.stop      = False

    def log(self, level, msg):
        self.logs.append((level, msg))

CAMP = _CampState()


def _campaign_worker(leads_data, msg_template, evo_url, evo_instance, evo_key,
                     pais_sel, test_mode):
    """Corre la campaña en un hilo de fondo. Escribe en CAMP, no en st.session_state."""
    try:
        total = len(leads_data)
        for idx, lead in enumerate(leads_data):
            if CAMP.stop:
                CAMP.log("warning", "🛑 Campaña detenida manualmente.")
                break

            mensaje = msg_template.replace("{nombre}", str(lead['nombre']))
            num = "".join(filter(str.isdigit, str(lead['telefono'])))
            if len(num) < 7:
                CAMP.log("warning", f"⚠️ Número inválido para {lead['nombre']}, saltando...")
                continue

            pref = COUNTRY_CODES.get(pais_sel, "")
            if pref and not num.startswith(pref):
                num = pref + num

            if test_mode:
                CAMP.log("info", f"🧪 [SIMULACIÓN] → {lead['nombre']} ({num})")
                time.sleep(1.5)
                sent_ok = True
                no_wa = False
            else:
                CAMP.log("info", f"📲 Enviando a {lead['nombre']} ({num})...")
                no_wa = False
                try:
                    r = requests.post(
                        f"{evo_url}/message/sendText/{evo_instance}",
                        json={
                            "number": num,
                            "options": {"delay": 1200, "presence": "composing", "linkPreview": True},
                            "textMessage": {"text": mensaje},
                        },
                        headers={
                            "apikey": evo_key,
                            "Content-Type": "application/json",
                            "ngrok-skip-browser-warning": "true",
                        },
                        timeout=20,
                    )
                    sent_ok = r.status_code in (200, 201)
                    if not sent_ok:
                        # Detectar si el número no tiene WhatsApp
                        try:
                            resp_data = r.json()
                            msgs = resp_data.get("response", {}).get("message", [])
                            if isinstance(msgs, list) and any(
                                isinstance(m, dict) and m.get("exists") is False for m in msgs
                            ):
                                no_wa = True
                                CAMP.log("warning", f"📵 {lead['nombre']} ({num}) — número sin WhatsApp, saltando")
                            else:
                                CAMP.log("error", f"❌ Error API (HTTP {r.status_code}): {r.text[:300]}")
                        except Exception:
                            CAMP.log("error", f"❌ Error API (HTTP {r.status_code}): {r.text[:300]}")
                except Exception as e:
                    sent_ok = False
                    CAMP.log("error", f"❌ Error de conexión: {e}")

            # Actualizar estado en DB según resultado
            new_status = None
            if sent_ok:
                new_status = "Contactado"
                label = "Simulado" if test_mode else "Enviado"
                CAMP.log("success", f"✅ {label} correctamente a {lead['nombre']}")
            elif no_wa:
                new_status = "Sin WhatsApp"

            if new_status:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(
                        "UPDATE leads SET estado=?, ultima_interaccion=? WHERE id=?",
                        (new_status, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), lead['id']),
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    CAMP.log("warning", f"⚠️ DB error: {e}")

            CAMP.progress = (idx + 1) / total

            # Pausa anti-ban entre envíos
            if idx < total - 1 and not CAMP.stop:
                espera = random.randint(8, 20) if test_mode else random.randint(120, 300)
                CAMP.log("info", f"⏳ Esperando {espera}s (anti-ban)...")
                for s in range(espera, 0, -1):
                    if CAMP.stop:
                        break
                    CAMP.countdown = s
                    time.sleep(1)
                CAMP.countdown = 0

        if not CAMP.stop:
            CAMP.log("success", "🎉 ¡Campaña completada exitosamente!")
    except Exception as e:
        CAMP.log("error", f"💥 Error fatal en campaña: {e}")
    finally:
        CAMP.running   = False
        CAMP.countdown = 0


AUTO_ZONAS = [
    "Centro", "Norte", "Sur", "Este", "Oeste",
    "Noreste", "Noroeste", "Sureste", "Suroeste",
    "Zona Industrial", "Zona Comercial", "Zona Residencial",
]

@st.cache_data(ttl=300)
def load_all_leads():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM leads", conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_search_history():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            "SELECT * FROM search_history ORDER BY id DESC LIMIT 200", conn
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def get_score(row):
    """Lead scoring automático basado en rating, reseñas y teléfono."""
    try:
        rating  = float(str(row.get('rating',  '0')).split('/')[0].strip().replace(',', '.'))
        reviews = int("".join(filter(str.isdigit, str(row.get('reseñas', '0')))) or 0)
    except Exception:
        return "❄️ Frío"
    has_phone = bool(row.get('telefono') and str(row.get('telefono')) not in ('N/A', '', 'None'))
    if rating >= 4.3 and reviews >= 30 and has_phone:
        return "🥇 Oro"
    if rating >= 3.8 and reviews >= 10 and has_phone:
        return "✅ Bueno"
    return "❄️ Frío"


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

if 'stop_requested'   not in st.session_state: st.session_state.stop_requested   = False
if 'total_session'    not in st.session_state: st.session_state.total_session    = 0
if 'skipped_session'  not in st.session_state: st.session_state.skipped_session  = 0
if 'last_summary'     not in st.session_state: st.session_state.last_summary     = None
if 'error_msg'        not in st.session_state: st.session_state.error_msg        = None
if 'geocerca_feature' not in st.session_state: st.session_state.geocerca_feature = None
if 'geocerca_grid_n'  not in st.session_state: st.session_state.geocerca_grid_n  = 3

# ---------------------------------------------------------------------------
# Page config & CSS
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Lead Gen ONYX", layout="wide", page_icon="⬛")

if st.session_state.error_msg:
    with st.container():
        st.error(f"Error detectado:\n\n{st.session_state.error_msg}")
        if st.button("Cerrar error"):
            st.session_state.error_msg = None
            st.rerun()

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

    /* ── Base ── */
    .stApp {
        background-color: #0C0C0E;
        font-family: 'Inter', sans-serif;
        color: #E8E8F0;
    }
    .stApp > header { background: transparent !important; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #111116 !important;
        border-right: 1px solid #1E1E28 !important;
    }
    @media (min-width: 768px) {
        [data-testid="stSidebar"] { min-width: 340px !important; }
    }

    /* ── Logo sidebar ── */
    .onyx-logo {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #FFFFFF;
        text-align: center;
        padding: 1.2rem 0 0.3rem;
        line-height: 1.2;
    }
    .onyx-logo span {
        background: linear-gradient(135deg, #FF0000 0%, #FF4444 50%, #FF0000 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        display: block;
        font-size: 1.75rem;
        letter-spacing: 0.2em;
    }
    .onyx-version {
        font-size: 0.65rem;
        color: #4A4A5A;
        text-align: center;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-top: 2px;
    }

    /* ── Expanders ── */
    [data-testid="stExpander"] {
        background: #16161E !important;
        border: 1px solid #1E1E28 !important;
        border-radius: 10px !important;
        margin-bottom: 8px;
    }
    [data-testid="stExpander"] summary {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #8888A0 !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        width: 100% !important;
        background: #16161E !important;
        color: #FF0000 !important;
        border: 1px solid #2A2A3A !important;
        border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 0.55rem 0.75rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: #FF0000 !important;
        color: #FFFFFF !important;
        border-color: #FF0000 !important;
        box-shadow: 0 0 18px rgba(255, 0, 0, 0.3) !important;
    }
    /* Primary button (INICIAR) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #CC0000, #FF2222) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 2px 12px rgba(255, 0, 0, 0.35) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #FF0000, #FF4444) !important;
        box-shadow: 0 4px 20px rgba(255, 0, 0, 0.5) !important;
        color: #FFFFFF !important;
    }

    /* ── Metrics ── */
    div[data-testid="stMetric"] {
        background: #16161E;
        border-radius: 12px;
        padding: 14px 16px !important;
        border: 1px solid #1E1E28;
        position: relative;
        overflow: hidden;
    }
    div[data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #FF0000, #880020);
        opacity: 0.7;
    }
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        color: #6A6A7A !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
    }

    /* ── Page header ── */
    .onyx-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #FFFFFF;
        line-height: 1;
        margin-bottom: 4px;
    }
    .onyx-header-red {
        background: linear-gradient(135deg, #FF0000 0%, #FF4444 50%, #FF0000 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .onyx-subtitle {
        font-size: 0.7rem;
        color: #4A4A5A;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 1.5rem;
    }

    /* ── Divider ── */
    hr {
        border: none;
        border-top: 1px solid #1E1E28 !important;
        margin: 1rem 0 !important;
    }

    /* ── Select / Input ── */
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: #16161E !important;
        border: 1px solid #2A2A3A !important;
        border-radius: 8px !important;
        color: #E8E8F0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.85rem !important;
    }
    .stSelectbox label, .stMultiSelect label,
    .stTextInput label, .stNumberInput label,
    .stSlider label, .stCheckbox label, .stToggle label {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        color: #6A6A7A !important;
    }

    /* ── Toggle / Checkbox ── */
    .stToggle [data-baseweb="checkbox"] span {
        background: #FF0000 !important;
    }

    /* ── Slider ── */
    .stSlider [data-baseweb="slider"] div[role="slider"] {
        background: #FF0000 !important;
    }

    /* ── Radio (vista) ── */
    .stRadio > div {
        background: #16161E;
        border-radius: 10px;
        padding: 6px 8px;
        border: 1px solid #1E1E28;
        gap: 4px;
    }
    .stRadio label {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: #6A6A7A !important;
    }

    /* ── Data Editor ── */
    .stDataFrame, [data-testid="stDataEditor"] {
        border-radius: 10px !important;
        overflow: hidden !important;
        border: 1px solid #1E1E28 !important;
    }

    /* ── Download button ── */
    .stDownloadButton > button {
        background: #16161E !important;
        color: #FF0000 !important;
        border: 1px solid #2A2A3A !important;
        border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        background: #FF0000 !important;
        color: #FFFFFF !important;
        border-color: #FF0000 !important;
    }

    /* ── Caption / small text ── */
    .stCaption, small, .stCaption p {
        color: #5A5A6A !important;
        font-size: 0.72rem !important;
    }

    /* ── Success / Warning / Error ── */
    .stSuccess { background: rgba(255, 0, 0, 0.06) !important; border-left: 3px solid #FF0000 !important; }
    .stWarning { background: rgba(200, 120, 40, 0.08) !important; border-left: 3px solid #C87828 !important; }
    .stError   { background: rgba(200, 30, 30, 0.10) !important; border-left: 3px solid #FF0000 !important; }

    /* ── Responsive ── */
    @media (max-width: 640px) {
        .onyx-header { font-size: 1.4rem; }
        div[data-testid="stMetric"] { margin-bottom: 8px; }
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div class='onyx-logo'>
            LEAD GEN
            <span>ONYX</span>
        </div>
        <div class='onyx-version'>Intelligence Platform &nbsp;·&nbsp; v2.1</div>
    """, unsafe_allow_html=True)
    st.divider()
    modo_escaneo = st.selectbox("Modo de escaneo", ["🎯 Caza-Sitios (Solo SIN web)", "📈 SEO Audit (Solo CON web)", "🔎 Full Scan (Todo)"])

    with st.expander("Geolocalización", expanded=True):
        pais_sel    = st.selectbox("País",   sorted(GEO_DATA.keys()))
        depto       = st.selectbox("Estado", sorted(GEO_DATA[pais_sel].keys()))
        ciudad_base = st.selectbox("Ciudad", sorted(GEO_DATA[pais_sel][depto]))
        st.divider()
        has_coords = ciudad_base in CITY_COORDS
        nivel = st.select_slider(
            "Cobertura",
            options=list(_NIVEL_CONFIG.keys()),
            value="🏙️ Normal  (9 puntos)",
        )
        usar_geocerca = st.toggle("Geocerca personalizada", bool(st.session_state.geocerca_feature))
        usar_manual   = st.checkbox("Barrios manuales", False) if not usar_geocerca else False

        if usar_geocerca:
            _gc_pts = generate_grid_in_feature(
                st.session_state.geocerca_feature,
                st.session_state.geocerca_grid_n,
            ) if st.session_state.geocerca_feature else []
            if _gc_pts:
                barrios = _gc_pts
                st.success(f"Geocerca activa · {len(_gc_pts)} puntos de búsqueda")
                if st.button("Limpiar geocerca", use_container_width=True):
                    st.session_state.geocerca_feature = None
                    st.rerun()
            else:
                barrios = [""]
                st.caption("Dibuja una zona en la vista Geocerca")
        elif usar_manual:
            barrios = [b.strip() for b in st.text_area("Barrios (uno por línea)", "Zona 1").split("\n") if b.strip()]
        else:
            _grid_n = _NIVEL_CONFIG[nivel]["grid_n"]
            if _grid_n == 1:
                barrios = [""]
                st.caption("Búsqueda general en toda la ciudad")
            else:
                _grid = generate_grid(ciudad_base, grid_n=_grid_n) if has_coords else None
                if _grid:
                    barrios = _grid
                    st.success(f"{len(_grid)} puntos GPS · {ciudad_base}")
                else:
                    barrios = AUTO_ZONAS
                    st.warning(f"{ciudad_base} sin coordenadas — usando {len(AUTO_ZONAS)} zonas de texto")

    with st.expander("Nicho y sector", expanded=True):
        cat       = st.selectbox("Categoría", list(NICHOS_DICT.keys()))
        sub       = st.selectbox("Nicho",     NICHOS_DICT[cat])
        exhaustivo = st.toggle("Exhaustivo total (+250)", False)
        usar_sinonimos = st.toggle("Sinónimos — búsqueda ampliada", True)
        nicho = "MODO_EXHAUSTIVO_TOTAL" if exhaustivo else (f"SECTOR_{cat}" if "TODOS" in sub else sub)
        extra_terms = NICHO_SYNONYMS.get(sub, []) if usar_sinonimos and not exhaustivo and "TODOS" not in sub else []

    max_res = st.number_input("Capacidad máxima", 5, 5000, 50)
    infinito = st.toggle("Ilimitado", False)
    st.divider()
    _n_terms = 1 + len(extra_terms)
    _n_zones = len(barrios) if barrios else 1
    _est = _n_zones * _n_terms
    st.caption(f"Estimado: {_n_zones} zonas × {_n_terms} término(s) = {_est} búsquedas")
    c1, c2 = st.columns(2)
    start_btn = c1.button("Iniciar", type="primary")
    stop_btn  = c2.button("Detener")
    if stop_btn:
        st.session_state.stop_requested = True

# ---------------------------------------------------------------------------
# Header & métricas
# ---------------------------------------------------------------------------
st.markdown("""
    <div class='onyx-header'>
        LEAD GEN &nbsp;<span class='onyx-header-red'>ONYX</span>
    </div>
    <div class='onyx-subtitle'>Prospección inteligente &nbsp;·&nbsp; Google Maps Intelligence</div>
""", unsafe_allow_html=True)

df_all = load_all_leads()

# Paleta de colores por status (usada en métricas y mapas)
STATUS_COLORS = {
    "Nuevo":       {"color": "#FF0000", "fill": "#FF0000", "opacity": 0.9},
    "Contactado":  {"color": "#6EB4C9", "fill": "#6EB4C9", "opacity": 0.85},
    "Interesado":  {"color": "#A06EC9", "fill": "#A06EC9", "opacity": 0.9},
    "Cerrado":     {"color": "#4ADE80", "fill": "#4ADE80", "opacity": 0.95},
    "Descartado":  {"color": "#555568", "fill": "#444455", "opacity": 0.5},
}

def _kpi_card(label, value, accent_color="#FF0000", subtext=None):
    sub_html = f"<div style='font-size:0.65rem;color:#555568;margin-top:2px;'>{subtext}</div>" if subtext else ""
    return (
        f"<div style='background:#16161E; border-radius:12px; padding:14px 16px; "
        f"border:1px solid #1E1E28; border-top:3px solid {accent_color}; height:100%;'>"
        f"  <div style='font-family:\"Space Grotesk\", sans-serif; font-size:0.6rem; "
        f"  font-weight:600; letter-spacing:0.12em; text-transform:uppercase; color:#6A6A7A;'>"
        f"  {label}</div>"
        f"  <div style='font-family:\"Space Grotesk\", sans-serif; font-size:1.8rem; "
        f"  font-weight:700; color:#FFFFFF; margin-top:2px; line-height:1.1;'>"
        f"  {value}</div>"
        f"  {sub_html}"
        f"</div>"
    )

# ── Fila 1: Sesión actual ───────────────────────────────────────────────
r1a, r1b, r1c, r1d = st.columns(4)
r1a.markdown(_kpi_card("Leads capturados", st.session_state.total_session, "#FF0000", "nuevos esta sesión"), unsafe_allow_html=True)
r1b.markdown(_kpi_card("Duplicados omitidos", st.session_state.skipped_session, "#555568", "ya existían en la DB"), unsafe_allow_html=True)
r1c.markdown(_kpi_card("Total en base de datos", len(df_all), "#FF0000"), unsafe_allow_html=True)
r1d.markdown(_kpi_card("Objetivo de búsqueda", "∞" if infinito else max_res, "#555568"), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

# ── Fila 2: Pipeline CRM ───────────────────────────────────────────────
r2cols = st.columns(5)
status_order = ["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado", "Sin WhatsApp"]

for col, status in zip(r2cols, status_order):
    count = len(df_all[df_all['estado'] == status])
    sc = STATUS_COLORS[status]
    col.markdown(_kpi_card(status, count, sc['color']), unsafe_allow_html=True)

log_container = st.empty()
if st.session_state.last_summary:
    s = st.session_state.last_summary
    st.success(
        f"Captura completada — **{s['leads']}** leads nuevos · "
        f"{s.get('dupes', 0)} duplicados omitidos"
    )
    st.button("Limpiar", on_click=lambda: setattr(st.session_state, 'last_summary', None))

# ---------------------------------------------------------------------------
# Vista CRM / Mapa
# ---------------------------------------------------------------------------
st.divider()
view_mode = st.radio("Vista de trabajo", ["🌓 Dividida", "🗺️ Mapa full", "📝 CRM full", "📊 Analytics", "🕐 Historial", "🚀 Campañas WA"], horizontal=True)


with st.expander("Filtrar y categorizar", expanded=False):
    f1, f2, f3, f4 = st.columns(4)
    nicho_f  = f1.multiselect("Nicho",     df_all['nicho'].unique())  if not df_all.empty else []
    tipo_f   = f2.multiselect("Categoría", df_all['tipo'].unique())   if not df_all.empty else []
    ciudad_f = f3.multiselect("Ciudad",    df_all['ciudad'].unique()) if not df_all.empty else []
    estado_f = f4.multiselect("Status",    ["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado", "Sin WhatsApp"])
    search_txt = st.text_input("Buscar por nombre o notas", placeholder="Escribe para filtrar...")

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
df_edit['Chat']  = df_edit.apply(lambda r: get_wa_link(r, pais_sel), axis=1)
df_edit['Score'] = df_edit.apply(get_score, axis=1)

_COL_CFG = {
    "estado":   st.column_config.SelectboxColumn("Status", options=["Nuevo", "Contactado", "Interesado", "Cerrado", "Descartado", "Sin WhatsApp"]),
    "Chat":     st.column_config.LinkColumn("Chat 📲"),
    "maps_url": st.column_config.LinkColumn("Maps 📍"),
    "web":      st.column_config.LinkColumn("Web"),
    "id":       None,
}

# ---------------------------------------------------------------------------
# Helpers de UI reutilizables
# ---------------------------------------------------------------------------
def _render_bulk_actions(df_filtered, country_name):
    """Sección de acciones en bulk + export WA para los leads filtrados."""
    if df_filtered.empty:
        return
    with st.expander(f"Acciones en bulk · {len(df_filtered)} leads filtrados", expanded=False):
        bc1, bc2, bc3 = st.columns([2, 1, 1])
        nuevo_estado = bc1.selectbox(
            "Cambiar estado a todos los filtrados",
            ["Contactado", "Interesado", "Cerrado", "Descartado", "Nuevo"],
            key="bulk_estado",
        )
        if bc2.button("Aplicar", type="primary", key="bulk_apply"):
            conn = sqlite3.connect(DB_PATH)
            ids = df_filtered['id'].tolist()
            conn.executemany(
                "UPDATE leads SET estado=? WHERE id=?",
                [(nuevo_estado, i) for i in ids]
            )
            conn.commit(); conn.close()
            load_all_leads.clear()
            st.toast(f"{len(ids)} leads actualizados a '{nuevo_estado}'")
            st.rerun()

        st.divider()
        st.markdown(
            "<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
            "letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;margin-bottom:8px;'>"
            "WhatsApp en batch</p>",
            unsafe_allow_html=True,
        )
        wa_rows = []
        for _, row in df_filtered.iterrows():
            link = get_wa_link(row, country_name)
            if link:
                wa_rows.append(f"{row['nombre']} — {link}")
        if wa_rows:
            wa_text = "\n".join(wa_rows)
            wc1, wc2 = st.columns(2)
            wc1.text_area(
                f"{len(wa_rows)} links generados",
                wa_text, height=180, key="wa_batch_area",
            )
            wc2.download_button(
                "Descargar lista WA",
                wa_text,
                file_name=f"whatsapp_leads_{datetime.datetime.now().strftime('%Y%m%d')}.txt",
                use_container_width=True,
            )
        else:
            st.caption("Ninguno de los leads filtrados tiene teléfono válido.")


# Paleta de colores por status (usada en ambos mapas)
STATUS_COLORS = {
    "Nuevo":       {"color": "#FF0000", "fill": "#FF0000", "opacity": 0.9},   # red
    "Contactado":  {"color": "#6EB4C9", "fill": "#6EB4C9", "opacity": 0.85},  # cyan
    "Interesado":  {"color": "#A06EC9", "fill": "#A06EC9", "opacity": 0.9},   # purple
    "Cerrado":     {"color": "#4ADE80", "fill": "#4ADE80", "opacity": 0.95},  # green
    "Descartado":  {"color": "#555568", "fill": "#444455", "opacity": 0.5},   # grey
}

def _status_color(estado):
    return STATUS_COLORS.get(estado, STATUS_COLORS["Nuevo"])

def _build_popup(row, pais_sel, compact=False):
    wa   = get_wa_link(row, pais_sel)
    maps = row.get('maps_url', '#')
    sc   = _status_color(row['estado'])
    pad  = "6px 10px" if compact else "10px 14px"
    badge = (f"<span style='background:{sc['color']};color:#0C0C0E;padding:2px 8px;"
             f"border-radius:4px;font-size:11px;font-weight:700;'>{row['estado']}</span>")
    html = (f"<div style='min-width:200px;font-family:Inter,sans-serif;'>"
            f"<b style='font-size:13px;'>{row['nombre']}</b><br>"
            f"<span style='color:#888;font-size:11px;'>⭐ {row['rating']} &nbsp;·&nbsp; {row['reseñas']} reseñas</span><br>"
            f"<div style='margin:6px 0'>{badge}</div><hr style='border-color:#333;margin:6px 0;'>")
    if wa:
        html += (f"<a href='{wa}' target='_blank' style='background:#25D366;color:white;padding:{pad};"
                 f"display:block;text-align:center;text-decoration:none;border-radius:6px;"
                 f"font-size:12px;font-weight:600;margin-bottom:6px;'>WhatsApp</a>")
    html += (f"<a href='{maps}' target='_blank' style='color:{sc['color']};text-align:center;"
             f"display:block;font-size:12px;font-weight:600;'>Ver en Google Maps</a></div>")
    return html

if view_mode == "🌓 Dividida":
    cl, cr = st.columns([0.45, 0.55])
    with cl:
        st.markdown("<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
                    "letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;margin-bottom:8px;'>"
                    "Mapa intel</p>", unsafe_allow_html=True)
        map_data = df_f.dropna(subset=['lat', 'lng']).copy()
        if not map_data.empty:
            import folium
            from streamlit_folium import st_folium
            total_map = len(map_data)
            contacted = len(map_data[map_data['estado'] != 'Nuevo'])
            pct = round(contacted / total_map * 100) if total_map else 0
            bar_fill = max(4, pct)
            # Leyenda compacta
            legend_items = "".join(
                f"<span style='display:inline-flex;align-items:center;gap:5px;"
                f"background:#1A1A22;border-radius:5px;padding:3px 8px;'>"
                f"<span style='width:8px;height:8px;border-radius:50%;background:{v['color']};flex-shrink:0;'></span>"
                f"<span style='font-size:11px;color:#C0C0D0;font-weight:500;'>{k}</span></span>"
                for k, v in STATUS_COLORS.items()
            )
            st.markdown(
                f"<div style='display:flex;flex-wrap:wrap;gap:5px;margin-bottom:12px;'>{legend_items}</div>"
                f"<div style='background:#16161E;border-radius:12px;padding:16px;border:1px solid #1E1E28;margin-bottom:12px;'>"
                f"  <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;'>"
                f"    <span style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;'>Porcentaje de Cobertura</span>"
                f"    <span style='font-family:Space Grotesk,sans-serif;font-size:2.2rem;font-weight:700;color:#FFFFFF;line-height:1;'>{pct}%</span>"
                f"  </div>"
                f"  <div style='background:#0C0C0E;border-radius:10px;height:10px;overflow:hidden;margin-bottom:8px;border:1px solid #1E1E28;'>"
                f"    <div style='width:{bar_fill}%;height:100%;background:#FF0000;border-radius:10px;'></div>"
                f"  </div>"
                f"  <div style='font-size:12px;color:#E8E8F0;font-weight:500;'>"
                f"    {contacted} contactados de {total_map} leads</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            from folium.plugins import MarkerCluster
            _MAP_LIMIT = 500
            render_data = map_data.head(_MAP_LIMIT)
            if len(map_data) > _MAP_LIMIT:
                st.caption(f"Mostrando {_MAP_LIMIT} de {len(map_data)} markers. Usa los filtros para ver zonas específicas.")
            m = folium.Map(location=[render_data["lat"].mean(), render_data["lng"].mean()],
                           zoom_start=12, tiles="CartoDB dark_matter")
            cluster = MarkerCluster(
                options={"maxClusterRadius": 40, "disableClusteringAtZoom": 15}
            ).add_to(m)
            for _, row in render_data.iterrows():
                sc = _status_color(row['estado'])
                folium.CircleMarker(
                    [row['lat'], row['lng']], radius=9,
                    color=sc['color'], fill=True, fill_color=sc['fill'],
                    fill_opacity=sc['opacity'], weight=1.5,
                    popup=folium.Popup(_build_popup(row, pais_sel, compact=True), max_width=260)
                ).add_to(cluster)
            st_folium(m, width=None, height=500, key="split_map", returned_objects=[])
        else:
            st.caption("Sin datos con coordenadas para mostrar.")
    with cr:
        st.markdown(f"<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
                    f"letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;margin-bottom:8px;'>"
                    f"CRM &nbsp;·&nbsp; {len(df_f)} leads</p>", unsafe_allow_html=True)
        edited_df = st.data_editor(
            df_edit[['id', 'Score', 'estado', 'notas', 'nombre', 'rating', 'Chat', 'maps_url']],
            column_config=_COL_CFG,
            disabled=["nombre", "rating", "Chat", "maps_url", "Score"],
            hide_index=True, width="stretch", height=500,
        )
        if st.button("Guardar CRM", type="primary"):
            conn = sqlite3.connect(DB_PATH)
            for _, r in edited_df.iterrows():
                conn.execute("UPDATE leads SET estado=?, notas=? WHERE id=?", (r['estado'], r['notas'], r['id']))
            conn.commit(); conn.close()
            load_all_leads.clear()
            st.rerun()
        _render_bulk_actions(df_f, pais_sel)

elif view_mode == "🗺️ Mapa full":
    map_data = df_f.dropna(subset=['lat', 'lng']).copy()
    if not map_data.empty:
        import folium
        from streamlit_folium import st_folium
        total_map = len(map_data)
        contacted = len(map_data[map_data['estado'] != 'Nuevo'])
        pct = round(contacted / total_map * 100) if total_map else 0
        bar_fill = max(4, pct)
        # Fila: barra de cobertura (columna ancha) + 5 cards de status
        cov_col, *stat_cols = st.columns([2.5, 1, 1, 1, 1, 1])
        cov_col.markdown(
            f"<div style='background:#16161E;border-radius:12px;padding:16px 20px;"
            f"border:1px solid #1E1E28;height:100%;display:flex;flex-direction:column;justify-content:center;'>"
            f"  <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
            f"    <div style='font-family:Space Grotesk,sans-serif;font-size:0.65rem;"
            f"font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;'>Cobertura del mapa</div>"
            f"    <div style='font-family:Space Grotesk,sans-serif;font-size:2.4rem;"
            f"font-weight:700;color:#FFFFFF;line-height:1;'>{pct}%</div>"
            f"  </div>"
            f"  <div style='background:#0C0C0E;border-radius:10px;height:12px;overflow:hidden;margin-bottom:8px;border:1px solid #1E1E28;'>"
            f"    <div style='width:{bar_fill}%;height:100%;background:#FF0000;border-radius:10px;'></div>"
            f"  </div>"
            f"  <div style='font-size:12px;color:#555568;'>{contacted} contactados / {total_map} totales</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        for col, (status, sc) in zip(stat_cols, STATUS_COLORS.items()):
            cnt = len(map_data[map_data['estado'] == status])
            col.markdown(
                f"<div style='background:#16161E;border-radius:12px;padding:16px 12px;"
                f"border:1px solid #1E1E28;border-top:4px solid {sc['color']};text-align:center;height:100%;'>"
                f"  <div style='font-family:Space Grotesk,sans-serif;font-size:1.8rem;"
                f"font-weight:700;color:#FFFFFF;line-height:1;'>{cnt}</div>"
                f"  <div style='font-family:Space Grotesk,sans-serif;font-size:0.6rem;"
                f"color:#6A6A7A;letter-spacing:0.08em;text-transform:uppercase;margin-top:6px;'>{status}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        from folium.plugins import MarkerCluster
        _MAP_LIMIT = 500
        render_data_full = map_data.head(_MAP_LIMIT)
        if len(map_data) > _MAP_LIMIT:
            st.caption(f"Mostrando {_MAP_LIMIT} de {len(map_data)} markers. Aplica filtros para ver zonas específicas.")
        m = folium.Map(location=[render_data_full["lat"].mean(), render_data_full["lng"].mean()],
                       zoom_start=13, tiles="CartoDB dark_matter")
        cluster_full = MarkerCluster(
            options={"maxClusterRadius": 50, "disableClusteringAtZoom": 14}
        ).add_to(m)
        for _, row in render_data_full.iterrows():
            sc = _status_color(row['estado'])
            folium.CircleMarker(
                [row['lat'], row['lng']], radius=11,
                color=sc['color'], fill=True, fill_color=sc['fill'],
                fill_opacity=sc['opacity'], weight=2,
                popup=folium.Popup(_build_popup(row, pais_sel), max_width=300)
            ).add_to(cluster_full)
        st_folium(m, width=None, height=720, key="full_map", returned_objects=[])
    else:
        st.caption("Sin datos con coordenadas para mostrar.")

elif view_mode == "📝 CRM full":
    with st.expander("➕ Añadir Prospecto Manualmente", expanded=False):
        st.markdown("Agrega un lead para que el bot de WhatsApp (Onyx) pueda atenderlo cuando te escriba, o para contactarlo desde la pestaña Campañas WA.")
        with st.form("add_lead_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            new_name = col1.text_input("Nombre / Empresa *")
            new_phone = col2.text_input("Teléfono (Ej: 573001234567) *", help="Incluye el código de país sin el signo +")
            new_niche = col3.text_input("Nicho / Categoría *", placeholder="Ej: Odontólogos, Restaurante...")
            
            col4, col5 = st.columns(2)
            new_city = col4.text_input("Ciudad", value=ciudad_base if 'ciudad_base' in locals() else "N/A")
            new_notes = col5.text_input("Notas / Contexto extra")
            
            submit_lead = st.form_submit_button("Guardar Prospecto", type="primary")
            if submit_lead:
                if new_name and new_phone and new_niche:
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute(
                            '''INSERT OR IGNORE INTO leads
                               (nombre, telefono, rating, reseñas, tipo, zona, ciudad, pais, nicho, fecha, estado, notas)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (new_name, new_phone, "N/A", "0", new_niche, "Manual", new_city, pais_sel, new_niche, datetime.datetime.now().strftime("%Y-%m-%d"), "Nuevo", new_notes)
                        )
                        conn.commit(); conn.close()
                        load_all_leads.clear()
                        st.success(f"✅ ¡Prospecto '{new_name}' guardado correctamente!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                else:
                    st.warning("⚠️ Nombre, Teléfono y Nicho son obligatorios.")
    
    edited_df = st.data_editor(
        df_edit[['id', 'Score', 'estado', 'notas', 'nombre', 'rating', 'reseñas', 'tipo', 'Chat', 'web', 'maps_url', 'nicho', 'fecha', 'ciudad']],
        column_config=_COL_CFG,
        disabled=["nombre", "rating", "reseñas", "tipo", "Chat", "web", "maps_url", "nicho", "fecha", "ciudad", "Score"],
        hide_index=True, width="stretch", height=700,
    )
    if st.button("Guardar cambios CRM", type="primary"):
        conn = sqlite3.connect(DB_PATH)
        for _, r in edited_df.iterrows():
            conn.execute("UPDATE leads SET estado=?, notas=? WHERE id=?", (r['estado'], r['notas'], r['id']))
        conn.commit(); conn.close()
        load_all_leads.clear()
        st.rerun()
    _render_bulk_actions(df_f, pais_sel)

elif view_mode == "📊 Analytics":
    if df_all.empty:
        st.info("Sin datos aún. Lanza tu primer escaneo para ver estadísticas.")
    else:
        df_all['score_label'] = df_all.apply(get_score, axis=1)

        # ── Fila de KPIs rápidos ──────────────────────────────────────────
        ka, kb, kc, kd = st.columns(4)
        total = len(df_all)
        oro   = len(df_all[df_all['score_label'] == '🥇 Oro'])
        bueno = len(df_all[df_all['score_label'] == '✅ Bueno'])
        frio  = len(df_all[df_all['score_label'] == '❄️ Frío'])
        ka.metric("Total leads", total)
        kb.metric("Oro (score máx)", oro, f"{round(oro/total*100)}%" if total else "0%")
        kc.metric("Bueno", bueno, f"{round(bueno/total*100)}%" if total else "0%")
        kd.metric("Fríos", frio, f"{round(frio/total*100)}%" if total else "0%")

        st.divider()

        ac1, ac2 = st.columns(2)

        # ── Leads por nicho ───────────────────────────────────────────────
        with ac1:
            st.markdown(
                "<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
                "letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;margin-bottom:6px;'>"
                "Leads por nicho</p>", unsafe_allow_html=True
            )
            nicho_counts = (
                df_all.groupby('nicho').size().reset_index(name='total')
                .sort_values('total', ascending=False).head(15)
            )
            chart_nicho = (
                alt.Chart(nicho_counts)
                .mark_bar(color='#FF0000', cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X('total:Q', title='Leads', axis=alt.Axis(labelColor='#6A6A7A', titleColor='#6A6A7A')),
                    y=alt.Y('nicho:N', sort='-x', title=None, axis=alt.Axis(labelColor='#C0C0D0')),
                    tooltip=['nicho:N', 'total:Q'],
                )
                .properties(height=350, background='#16161E')
                .configure_view(strokeWidth=0)
                .configure_axis(gridColor='#1E1E28', domainColor='#1E1E28')
            )
            st.altair_chart(chart_nicho, use_container_width=True)

        # ── Distribución de status ────────────────────────────────────────
        with ac2:
            st.markdown(
                "<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
                "letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;margin-bottom:6px;'>"
                "Pipeline de ventas</p>", unsafe_allow_html=True
            )
            STATUS_CHART_COLORS = {
                "Nuevo": "#FF0000", "Contactado": "#6EB4C9",
                "Interesado": "#A06EC9", "Cerrado": "#4ADE80", "Descartado": "#555568",
            }
            estado_counts = (
                df_all.groupby('estado').size().reset_index(name='total')
            )
            estado_counts['color'] = estado_counts['estado'].map(
                lambda s: STATUS_CHART_COLORS.get(s, '#888888')
            )
            chart_estado = (
                alt.Chart(estado_counts)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X('total:Q', title='Leads', axis=alt.Axis(labelColor='#6A6A7A', titleColor='#6A6A7A')),
                    y=alt.Y('estado:N', sort='-x', title=None, axis=alt.Axis(labelColor='#C0C0D0')),
                    color=alt.Color('color:N', scale=None, legend=None),
                    tooltip=['estado:N', 'total:Q'],
                )
                .properties(height=200, background='#16161E')
                .configure_view(strokeWidth=0)
                .configure_axis(gridColor='#1E1E28', domainColor='#1E1E28')
            )
            st.altair_chart(chart_estado, use_container_width=True)

            st.markdown(
                "<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
                "letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;margin:16px 0 6px;'>"
                "Score breakdown</p>", unsafe_allow_html=True
            )
            score_counts = (
                df_all['score_label'].value_counts().reset_index()
                .rename(columns={'index': 'score', 'score_label': 'total', 'count': 'total'})
            )
            score_counts.columns = ['score', 'total']
            SCORE_COLORS = {'🥇 Oro': '#F5C518', '✅ Bueno': '#4ADE80', '❄️ Frío': '#6A6A7A'}
            score_counts['color'] = score_counts['score'].map(
                lambda s: SCORE_COLORS.get(s, '#888')
            )
            chart_score = (
                alt.Chart(score_counts)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X('total:Q', title='Leads', axis=alt.Axis(labelColor='#6A6A7A', titleColor='#6A6A7A')),
                    y=alt.Y('score:N', sort='-x', title=None, axis=alt.Axis(labelColor='#C0C0D0')),
                    color=alt.Color('color:N', scale=None, legend=None),
                    tooltip=['score:N', 'total:Q'],
                )
                .properties(height=130, background='#16161E')
                .configure_view(strokeWidth=0)
                .configure_axis(gridColor='#1E1E28', domainColor='#1E1E28')
            )
            st.altair_chart(chart_score, use_container_width=True)

        # ── Evolución temporal ────────────────────────────────────────────
        st.divider()
        st.markdown(
            "<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
            "letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;margin-bottom:6px;'>"
            "Leads capturados por día</p>", unsafe_allow_html=True
        )
        if 'fecha' in df_all.columns:
            daily = (
                df_all.groupby('fecha').size().reset_index(name='leads')
                .sort_values('fecha')
            )
            chart_time = (
                alt.Chart(daily)
                .mark_area(
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[
                            alt.GradientStop(color='rgba(255,0,0,0.6)', offset=0),
                            alt.GradientStop(color='rgba(255,0,0,0.05)', offset=1),
                        ],
                        x1=0, x2=0, y1=1, y2=0,
                    ),
                    line={'color': '#FF0000', 'strokeWidth': 2},
                )
                .encode(
                    x=alt.X('fecha:T', title=None, axis=alt.Axis(labelColor='#6A6A7A', format='%d %b')),
                    y=alt.Y('leads:Q', title='Leads', axis=alt.Axis(labelColor='#6A6A7A', titleColor='#6A6A7A')),
                    tooltip=[alt.Tooltip('fecha:T', format='%Y-%m-%d'), 'leads:Q'],
                )
                .properties(height=200, background='#16161E')
                .configure_view(strokeWidth=0)
                .configure_axis(gridColor='#1E1E28', domainColor='#1E1E28')
            )
            st.altair_chart(chart_time, use_container_width=True)

elif view_mode == "🕐 Historial":
    df_hist = load_search_history()
    if df_hist.empty:
        st.info("Aún no hay búsquedas registradas. El historial se llena automáticamente al escanear.")
    else:
        # KPIs del historial
        hk1, hk2, hk3, hk4 = st.columns(4)
        hk1.metric("Búsquedas realizadas", len(df_hist))
        hk2.metric("Leads nuevos (total)", int(df_hist['leads_nuevos'].sum()))
        hk3.metric("Duplicados omitidos",  int(df_hist['leads_duplicados'].sum()))
        tasa_dup = df_hist['leads_duplicados'].sum() / max(
            df_hist['leads_nuevos'].sum() + df_hist['leads_duplicados'].sum(), 1
        ) * 100
        hk4.metric("Tasa de duplicados", f"{round(tasa_dup)}%")

        st.divider()
        st.markdown(
            "<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
            "letter-spacing:0.1em;text-transform:uppercase;color:#6A6A7A;margin-bottom:8px;'>"
            "Registro de búsquedas</p>", unsafe_allow_html=True
        )
        st.dataframe(
            df_hist[['fecha', 'ciudad', 'pais', 'nicho', 'zona', 'leads_nuevos', 'leads_duplicados']],
            hide_index=True,
            use_container_width=True,
            height=500,
            column_config={
                'fecha':            st.column_config.TextColumn("Fecha"),
                'ciudad':           st.column_config.TextColumn("Ciudad"),
                'pais':             st.column_config.TextColumn("País"),
                'nicho':            st.column_config.TextColumn("Nicho"),
                'zona':             st.column_config.TextColumn("Zona"),
                'leads_nuevos':     st.column_config.NumberColumn("Nuevos", format="%d"),
                'leads_duplicados': st.column_config.NumberColumn("Dupes",  format="%d"),
            }
        )
        if st.button("Limpiar historial"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM search_history")
            conn.commit(); conn.close()
            load_search_history.clear()
            st.rerun()

# ---------------------------------------------------------------------------
# Fase 2 & 3: Campañas de WhatsApp e Integración con Evolution API
# ---------------------------------------------------------------------------
elif view_mode == "🚀 Campañas WA":
    # ── Configuración Evolution API en el sidebar ──
    with st.sidebar:
        st.divider()
        st.markdown("**Configuración Evolution API**")
        if 'evo_instance_name' not in st.session_state:
            st.session_state.evo_instance_name = os.getenv("EVO_INSTANCE", "onyxbot")

        evo_url_input = st.text_input("URL Evolution", os.getenv("EVO_URL", ""), placeholder="https://tu-tunel.ngrok-free.app")
        evo_key       = st.text_input("API Key", os.getenv("EVO_API_KEY", ""))
        evo_instance  = st.text_input("Instancia", value=st.session_state.evo_instance_name).lower().strip()
        st.session_state.evo_instance_name = evo_instance
        evo_url = evo_url_input.strip().rstrip("/")
        
        if st.button("📱 Panel de Conexión / QR", use_container_width=True):
            if not evo_url or not evo_url.startswith("http"):
                st.warning("⚠️ Pega la URL de ngrok primero.")
            else:
                st.session_state.show_qr = True

        if evo_url:
            st.markdown(f"[🔗 Abrir Manager Oficial]({evo_url}/manager)", help="Si el QR no carga aquí, usa este panel oficial.")

        if st.button("🔴 Borrar Bot / Limpiar", use_container_width=True):
            try:
                headers_del = {"apikey": evo_key, "ngrok-skip-browser-warning": "true"}
                requests.delete(f"{evo_url}/instance/logout/{evo_instance}", headers=headers_del)
                requests.delete(f"{evo_url}/instance/delete/{evo_instance}", headers=headers_del)
                st.success("✅ Servidor limpio.")
                st.session_state.evo_instance_name = f"bot{random.randint(100,999)}"
                st.rerun()
            except: st.error("No se pudo borrar.")

    st.markdown("<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#6A6A7A;margin-bottom:12px;'>Campaña automatizada</p>", unsafe_allow_html=True)

    if st.session_state.get('show_qr', False):
        with st.container():
            st.markdown("<div style='background:#16161E; padding:20px; border-radius:15px; border:2px solid #FF0000; text-align:center;'>", unsafe_allow_html=True)
            st.subheader("🔗 Vinculación de WhatsApp")
            try:
                headers = {"apikey": evo_key, "Authorization": f"Bearer {evo_key}", "ngrok-skip-browser-warning": "true"}
                
                with st.expander("🛠️ Ver logs de conexión paso a paso", expanded=True):
                    log_c = st.empty()
                
                # Check actual state
                state_url = f"{evo_url}/instance/connectionState/{evo_instance}"
                log_c.info(f"1️⃣ Consultando estado: GET {state_url}")
                r_state = requests.get(state_url, headers=headers, timeout=10)
                log_c.write(f"👉 Respuesta (HTTP {r_state.status_code}): {r_state.text[:100]}")
                
                if r_state.status_code == 404:
                    log_c.warning("2️⃣ El bot no existe. Mandando orden de crearlo...")
                    st.info("Configurando bot nuevo...")
                    res_c = requests.post(f"{evo_url}/instance/create", json={"instanceName": evo_instance, "token": evo_key, "integration": "WHATSAPP-BAILEYS", "qrcode": True}, headers=headers, timeout=15)
                    log_c.write(f"👉 Respuesta de creación (HTTP {res_c.status_code}): {res_c.text[:100]}")
                    time.sleep(6)
                    log_c.info("3️⃣ Volviendo a consultar estado...")
                    r_state = requests.get(state_url, headers=headers, timeout=10)
                    log_c.write(f"👉 Respuesta (HTTP {r_state.status_code}): {r_state.text[:100]}")

                if r_state.status_code == 200:
                    state_data = r_state.json()
                    status = state_data.get('instance', {}).get('state', 'unknown')
                    log_c.success(f"📌 Estado detectado: '{status}'")

                    qr_img = None
                    if status == 'connecting':
                        log_c.info("4️⃣ El estado es 'connecting'. Solicitando código QR...")
                        
                        # Intentar obtener el QR hasta 3 veces porque a veces la API tarda en generarlo
                        for intento in range(1, 4):
                            r_qr = requests.get(f"{evo_url}/instance/connect/{evo_instance}?apikey={evo_key}", headers=headers, timeout=15)
                            log_c.write(f"👉 Respuesta QR (Intento {intento}) HTTP {r_qr.status_code}: {r_qr.text[:150]}")
                            
                            if r_qr.status_code == 200:
                                qr_json = r_qr.json()
                                qr_img = qr_json.get('base64')
                                if not qr_img and qr_json.get('qrcode', {}).get('base64'):
                                    qr_img = qr_json.get('qrcode', {}).get('base64')
                                
                                if qr_img:
                                    log_c.success("✅ Imagen QR obtenida.")
                                    break
                                else:
                                    log_c.warning(f"⚠️ Sin imagen Base64 en el intento {intento}. Esperando 3s...")
                                    time.sleep(3)
                            else:
                                break

                    if status in ('open', 'connected'):
                        st.success("✅ ¡WhatsApp vinculado!")
                    elif qr_img:
                        st.image(qr_img, width=300, caption="Escanea con tu celular")
                    else:
                        st.warning(f"Estado del motor: {status}")
                        c1, c2 = st.columns(2)
                        if c1.button("🔌 Despertar Motor"):
                            requests.post(f"{evo_url}/instance/restart/{evo_instance}", headers=headers)
                            st.rerun()
                        if c2.button("☢️ Reiniciar Todo"):
                            requests.delete(f"{evo_url}/instance/delete/{evo_instance}", headers=headers)
                            st.session_state.evo_instance_name = f"bot{random.randint(1000,9999)}"
                            st.rerun()
                        
                        st.markdown("---")
                        st.write("**Vincular con Código**")
                        c_pref = COUNTRY_CODES.get(pais_sel, "57")
                        num_in = st.text_input("Número", placeholder=f"Ej: {c_pref}310...")
                        if st.button("🔢 Generar Código"):
                            if num_in:
                                clean_n = "".join(filter(str.isdigit, num_in))
                                if not clean_n.startswith(c_pref): clean_n = c_pref + clean_n
                                log_c.info(f"Pidiendo código para {clean_n}...")
                                rp = requests.get(f"{evo_url}/instance/connect/pairing/{evo_instance}?number={clean_n}", headers=headers)
                                log_c.write(f"👉 Respuesta código (HTTP {rp.status_code}): {rp.text[:100]}")
                                if rp.status_code == 200:
                                    st.code(rp.json().get('code'), language="text")
                                    st.write("Escríbelo en tu celular.")
                                else: st.error(f"Error {rp.status_code}")
                            else: st.warning("Escribe el número.")
                else: 
                    log_c.error("❌ La API devolvió un error al consultar el estado.")
                    st.error(f"API: {r_state.text}")
            except Exception as e: 
                st.error(f"Error interno: {e}")
            if st.button("Cerrar Ventana"): st.session_state.show_qr = False; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.divider()

    df_camp = df_all.copy()
    df_camp = df_camp[df_camp['telefono'].notna() & (df_camp['telefono'] != 'N/A')]
    df_camp = df_camp[df_camp['estado'] == 'Nuevo']
    df_camp = df_camp[df_camp['bot_pausado'].fillna(0).astype(int) == 0]

    if df_camp.empty:
        st.info("No hay prospectos 'Nuevos' con teléfono válido para contactar.")
    else:
        # ── Opciones de Prueba (Simulación) ──
        st.markdown("---")
        mode_cols = st.columns(2)
        test_mode = mode_cols[0].toggle("🧪 Modo Simulación (Probar sin API)", False, help="Si está activo, no enviará mensajes reales pero actualizará la DB y mostrará los tiempos.")
        manual_mode = mode_cols[1].toggle("🔗 Mostrar links manuales", False)

        if test_mode:
            st.warning("⚠️ MODO SIMULACIÓN ACTIVO: Los mensajes NO llegarán a los clientes.")
        else:
            st.success("✅ MODO REAL ACTIVO: Se enviarán mensajes reales vía WhatsApp.")

        cc1, cc2 = st.columns([0.6, 0.4])
        with cc1:
            st.markdown("**Redactor de mensaje**")
            msg_template = st.text_area(
                "Usa {nombre} para personalizar el mensaje",
                "Hola {nombre}, vi tu negocio en Google Maps y me gustaría comentarte algo. ¿Hablamos?",
                height=150
            )
            preview_lead = df_camp.iloc[0]
            st.caption(f"Previsualización: {msg_template.replace('{nombre}', preview_lead['nombre'])}")
            
        with cc2:
            st.markdown("**Selección de Lote**")
            batch_size = st.number_input("Pre-seleccionar cantidad", 1, len(df_camp) if len(df_camp) > 0 else 1, min(15, len(df_camp)) if len(df_camp) > 0 else 1)
            st.warning("⚠️ Recomendamos no enviar más de 20 mensajes diarios para evitar baneos.")
            
        st.markdown("---")

        # Mostrar tabla de leads (solo lectura)
        lote_leads = df_camp.head(int(batch_size))
        st.dataframe(
            lote_leads[['nombre', 'nicho', 'telefono', 'ciudad']],
            hide_index=True,
            use_container_width=True,
            height=300,
        )

        if manual_mode:
            st.markdown("**Envío Manual / Herramientas Externas**")
            lista_numeros = []
            lista_mensajes = []
            for _, l in lote_leads.iterrows():
                num = "".join(filter(str.isdigit, str(l['telefono'])))
                pref = COUNTRY_CODES.get(pais_sel, "")
                if pref and not num.startswith(pref): num = pref + num
                lista_numeros.append(num)
                lista_mensajes.append(f"{num}: {msg_template.replace('{nombre}', l['nombre'])}")
            col_copy1, col_copy2 = st.columns(2)
            col_copy1.markdown("**📋 Números**")
            col_copy1.code("\n".join(lista_numeros), language="text")
            col_copy2.markdown("**📋 Mensajes**")
            col_copy2.code("\n".join(lista_mensajes), language="text")
            st.caption("Usa estos botones para pegar los datos en extensiones como WA Web Plus o Bulk Sender.")
            with st.expander("Abrir chats uno por uno", expanded=True):
                for _, l in lote_leads.iterrows():
                    link = get_wa_link(l, pais_sel)
                    if link:
                        st.link_button(f"Enviar a {l['nombre']}", link, use_container_width=True)

        st.info(f"Lista de envío: {len(lote_leads)} prospectos")

        def _do_start():
            st.session_state["_camp_go"] = True
        def _do_stop():
            CAMP.stop = True

        c_on, c_off = st.columns(2)
        c_on.button("🚀 INICIAR CAMPAÑA", key="btn_camp_start", type="primary",
                     disabled=CAMP.running, on_click=_do_start)
        c_off.button("🛑 DETENER", key="btn_camp_stop",
                      disabled=not CAMP.running, on_click=_do_stop)

        if st.session_state.pop("_camp_go", False) and not CAMP.running:
            if not evo_url and not test_mode:
                st.error("❌ Ingresa la URL de Evolution API antes de iniciar.")
            elif len(lote_leads) == 0:
                st.error("❌ No hay leads seleccionados.")
            else:
                leads_list = lote_leads[['id', 'nombre', 'telefono']].to_dict('records')
                CAMP.reset()
                t = threading.Thread(
                    target=_campaign_worker,
                    args=(leads_list, msg_template, evo_url, evo_instance,
                          evo_key, pais_sel, test_mode),
                    daemon=True,
                )
                t.start()
                st.rerun()

        # ── Panel de estado de la campaña ──
        if CAMP.logs or CAMP.running:
            st.markdown("---")
            if CAMP.running:
                if CAMP.countdown > 0:
                    st.progress(CAMP.progress, text=f"⏳ Próximo envío en {CAMP.countdown}s (anti-ban)...")
                else:
                    st.progress(CAMP.progress, text="📤 Enviando mensaje...")
            else:
                st.progress(CAMP.progress, text="Campaña finalizada")

            log_box = st.container()
            for (lvl, msg) in CAMP.logs[-50:]:
                if   lvl == "success": log_box.success(msg)
                elif lvl == "error":   log_box.error(msg)
                elif lvl == "warning": log_box.warning(msg)
                else:                  log_box.info(msg)

            if CAMP.running:
                time.sleep(0.3)
                st.rerun()
            else:
                load_all_leads.clear()

elif view_mode == "📐 Geocerca":
    import folium
    from folium.plugins import Draw
    from streamlit_folium import st_folium

    st.markdown(
        "<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
        "letter-spacing:0.12em;text-transform:uppercase;color:#6A6A7A;margin-bottom:12px;'>"
        "Dibuja la zona de búsqueda — círculo, polígono o rectángulo</p>",
        unsafe_allow_html=True,
    )

    # ── Controles de densidad de la grilla ───────────────────────────────────
    gc1, gc2, gc3 = st.columns([3, 1, 1])
    with gc1:
        gc_nivel = st.select_slider(
            "Densidad de búsqueda dentro de la geocerca",
            options=list(_NIVEL_CONFIG.keys()),
            value=list(_NIVEL_CONFIG.keys())[
                [c["grid_n"] for c in _NIVEL_CONFIG.values()].index(
                    st.session_state.geocerca_grid_n
                )
            ],
            key="gc_nivel_slider",
        )
        st.session_state.geocerca_grid_n = _NIVEL_CONFIG[gc_nivel]["grid_n"]
    with gc2:
        if st.button("Limpiar geocerca", use_container_width=True, key="gc_clear"):
            st.session_state.geocerca_feature = None
            st.rerun()
    with gc3:
        _gc_preview = generate_grid_in_feature(
            st.session_state.geocerca_feature, st.session_state.geocerca_grid_n
        )
        if _gc_preview:
            st.markdown(
                f"<div style='background:#16161E;border-radius:10px;padding:10px;border:1px solid #1E1E28;"
                f"text-align:center;'>"
                f"<div style='font-family:Space Grotesk,sans-serif;font-size:1.6rem;font-weight:700;"
                f"color:#FF0000;'>{len(_gc_preview)}</div>"
                f"<div style='font-size:0.65rem;color:#6A6A7A;text-transform:uppercase;"
                f"letter-spacing:0.1em;'>puntos GPS</div></div>",
                unsafe_allow_html=True,
            )

    # ── Mapa de dibujo ────────────────────────────────────────────────────────
    centroid = feature_centroid(st.session_state.geocerca_feature)
    map_center = centroid if centroid else (4.711, -74.0721)  # Bogotá por defecto
    gc_map = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB dark_matter")

    Draw(
        draw_options={
            "polyline":     False,
            "polygon":      True,
            "circle":       True,
            "rectangle":    True,
            "circlemarker": False,
            "marker":       False,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(gc_map)

    # Mostrar la geocerca guardada como capa GeoJSON
    if st.session_state.geocerca_feature:
        feat = st.session_state.geocerca_feature
        geom = feat.get("geometry", {})

        # Dibujar el contorno
        if geom.get("type") == "Point" and "radius" in feat.get("properties", {}):
            # Círculo: dibujarlo como CircleMarker con el radio real
            lat, lng = feat["properties"].get("_lat", map_center[0]), map_center[1]
            c_lng, c_lat = geom["coordinates"]
            folium.Circle(
                [c_lat, c_lng],
                radius=feat["properties"]["radius"],
                color="#FF0000", fill=True, fill_opacity=0.12, weight=2,
                dash_array="6",
            ).add_to(gc_map)
        else:
            folium.GeoJson(
                feat,
                style_function=lambda _: {
                    "color": "#FF0000", "fillColor": "#FF0000",
                    "weight": 2, "fillOpacity": 0.10, "dashArray": "6",
                },
            ).add_to(gc_map)

        # Puntos de búsqueda previstos
        for coord_str in _gc_preview:
            _, coords_part = coord_str.split(":", 1)
            clat, clng, _ = coords_part.split(",")
            folium.CircleMarker(
                [float(clat), float(clng)], radius=6,
                color="#FF0000", fill=True, fill_color="#FF0000",
                fill_opacity=0.7, weight=1.5,
                tooltip="Punto de búsqueda",
            ).add_to(gc_map)

    gc_result = st_folium(
        gc_map,
        width=None, height=560,
        key="geocerca_draw_map",
        returned_objects=["all_drawings"],
    )

    # Capturar nuevo dibujo
    drawings = (gc_result or {}).get("all_drawings") or []
    if drawings:
        last = drawings[-1]
        # Comparar con el guardado para no re-guardar en cada rerun
        import json
        if json.dumps(last, sort_keys=True) != json.dumps(
            st.session_state.geocerca_feature, sort_keys=True
        ):
            st.session_state.geocerca_feature = last
            st.rerun()

    # Instrucciones
    if not st.session_state.geocerca_feature:
        st.markdown(
            "<div style='background:#16161E;border:1px dashed #2A2A3A;border-radius:10px;"
            "padding:18px 20px;margin-top:12px;'>"
            "<p style='font-family:Space Grotesk,sans-serif;font-size:0.75rem;color:#6A6A7A;"
            "margin:0;line-height:1.8;'>"
            "<b style='color:#FFFFFF;'>Cómo usar:</b><br>"
            "1. Usa las herramientas del mapa (esquina superior izquierda) para dibujar<br>"
            "2. Círculo, polígono o rectángulo — elige el que prefieras<br>"
            "3. La app genera automáticamente una grilla de puntos GPS dentro<br>"
            "4. Activa <b>Geocerca personalizada</b> en el sidebar y lanza el escaneo"
            "</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.success(
            f"Geocerca lista — {len(_gc_preview)} puntos de búsqueda generados. "
            f"Activa 'Geocerca personalizada' en el sidebar y presiona Iniciar."
        )

# ---------------------------------------------------------------------------
# Export & Admin
# ---------------------------------------------------------------------------
st.divider()
import os, shutil, tempfile

# ── Fila de exportación ──────────────────────────────────────────────────────
ex1, ex2, ex3 = st.columns(3)
with ex1:
    st.download_button(
        "Exportar CSV",
        df_all.to_csv(index=False),
        f"leads_onyx_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
        use_container_width=True,
    )
with ex2:
    with open(DB_PATH, "rb") as _f:
        st.download_button(
            "Descargar backup DB",
            _f.read(),
            f"leads_onyx_{datetime.datetime.now().strftime('%Y%m%d')}.db",
            mime="application/octet-stream",
            use_container_width=True,
        )
with ex3:
    with st.expander("Admin base de datos"):
        if st.button("Compactar DB", use_container_width=True):
            conn = sqlite3.connect(DB_PATH); conn.execute("VACUUM"); conn.close()
            load_all_leads.clear(); st.success("Base de datos compactada")
        if st.button("Borrar todos los leads", use_container_width=True):
            if st.session_state.get('confirm_del', False):
                conn = sqlite3.connect(DB_PATH)
                conn.execute("DELETE FROM leads"); conn.commit(); conn.close()
                load_all_leads.clear()
                st.session_state.confirm_del = False; st.rerun()
            else:
                st.warning("Confirma para borrar todos los datos")
                st.session_state.confirm_del = True

# ── Restaurar backup ─────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='font-family:Space Grotesk,sans-serif;font-size:0.7rem;font-weight:600;"
    "letter-spacing:0.12em;text-transform:uppercase;color:#6A6A7A;margin-bottom:10px;'>"
    "Restaurar base de datos</p>",
    unsafe_allow_html=True,
)
rb1, rb2 = st.columns(2)

with rb1:
    st.markdown(
        "<p style='font-size:0.75rem;color:#8888A0;margin-bottom:6px;'>"
        "Subir backup <code>.db</code> — reemplaza la base de datos actual</p>",
        unsafe_allow_html=True,
    )
    uploaded_db = st.file_uploader("Archivo .db", type=["db"], key="upload_db", label_visibility="collapsed")
    if uploaded_db:
        if st.button("Restaurar desde .db", type="primary", use_container_width=True):
            try:
                # Validar que sea un SQLite válido antes de reemplazar
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
                tmp.write(uploaded_db.read())
                tmp.flush()
                test_conn = sqlite3.connect(tmp.name)
                tables = test_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                test_conn.close()
                table_names = [t[0] for t in tables]
                if "leads" not in table_names:
                    st.error("El archivo no contiene una tabla 'leads' válida.")
                else:
                    shutil.copy2(tmp.name, DB_PATH)
                    os.unlink(tmp.name)
                    init_db()  # asegura que existan todas las columnas
                    load_all_leads.clear()
                    load_search_history.clear()
                    st.success(f"Base de datos restaurada — {len(table_names)} tablas encontradas")
                    st.rerun()
            except Exception as e:
                st.error(f"Error al restaurar: {e}")

with rb2:
    st.markdown(
        "<p style='font-size:0.75rem;color:#8888A0;margin-bottom:6px;'>"
        "Importar desde <code>.csv</code> — fusiona leads al existente sin borrar nada</p>",
        unsafe_allow_html=True,
    )
    uploaded_csv = st.file_uploader("Archivo .csv", type=["csv"], key="upload_csv", label_visibility="collapsed")
    if uploaded_csv:
        if st.button("Importar desde CSV", type="primary", use_container_width=True):
            try:
                df_import = pd.read_csv(uploaded_csv)
                required = {"nombre", "ciudad"}
                missing = required - set(df_import.columns.str.lower())
                if missing:
                    st.error(f"El CSV no tiene las columnas requeridas: {missing}")
                else:
                    df_import.columns = df_import.columns.str.lower()
                    conn = sqlite3.connect(DB_PATH)
                    inserted = 0
                    for _, r in df_import.iterrows():
                        cur = conn.execute(
                            '''INSERT OR IGNORE INTO leads
                               (nombre, telefono, rating, reseñas, tipo, lat, lng,
                                zona, ciudad, pais, nicho, fecha, web, maps_url, estado, notas)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (
                                r.get('nombre'), r.get('telefono'), r.get('rating'),
                                r.get('reseñas', r.get('resenas', '0')),
                                r.get('tipo'), r.get('lat'), r.get('lng'),
                                r.get('zona'), r.get('ciudad'), r.get('pais'),
                                r.get('nicho'), r.get('fecha'),
                                r.get('web', r.get('sitio web')),
                                r.get('maps_url'), r.get('estado', 'Nuevo'),
                                r.get('notas'),
                            )
                        )
                        inserted += cur.rowcount
                    conn.commit(); conn.close()
                    load_all_leads.clear()
                    st.success(f"{inserted} leads importados · {len(df_import) - inserted} duplicados omitidos")
                    st.rerun()
            except Exception as e:
                st.error(f"Error al importar CSV: {e}")

# ---------------------------------------------------------------------------
# Lanzar scraping
# ---------------------------------------------------------------------------
if start_btn:
    st.session_state.last_summary   = None
    st.session_state.stop_requested = False
    st.session_state.total_session  = 0
    st.session_state.skipped_session = 0
    live_c       = log_container.empty()
    progress_bar = st.progress(0, text="Preparando escaneo...")
    with st.expander("Logs de prospección", expanded=True):
        try:
            _run_async(main_loop(
                nicho, ciudad_base, pais_sel, barrios,
                max_res, infinito, modo_escaneo,
                st, NICHOS_DICT, live_c, progress_bar, extra_terms,
            ))
        except Exception as e:
            import traceback
            st.session_state.error_msg = f"{e}\n\n{traceback.format_exc()}"
    # Toast de notificación al terminar
    if st.session_state.last_summary:
        s = st.session_state.last_summary
        st.toast(
            f"Escaneo completado — {s['leads']} nuevos · {s.get('dupes', 0)} duplicados",
            icon="✅",
        )
    load_all_leads.clear()
    load_search_history.clear()
    st.rerun()

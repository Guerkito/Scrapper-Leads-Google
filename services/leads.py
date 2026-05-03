import urllib.parse
import sqlite3
import pandas as pd
from services.constants import COUNTRY_CODES
from db import DB_PATH, open_conn

def load_all_leads():
    """Carga todos los leads desde la base de datos de forma segura."""
    try:
        conn = open_conn()
        df = pd.read_sql_query("SELECT * FROM leads", conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error cargando leads: {e}")
        return pd.DataFrame()

def get_score(row):
    """Lead scoring automático basado en rating, reseñas y teléfono."""
    try:
        rating_str = str(row.get('rating', '0')).split('/')[0].strip().replace(',', '.')
        rating = float(rating_str)
        reviews_str = "".join(filter(str.isdigit, str(row.get('reseñas', '0'))))
        reviews = int(reviews_str or 0)
    except (ValueError, IndexError, AttributeError):
        return "❄️ Frío"
    
    has_phone = bool(row.get('telefono') and str(row.get('telefono')) not in ('N/A', '', 'None'))
    
    if rating >= 4.3 and reviews >= 30 and has_phone:
        return "🥇 Oro"
    if rating >= 3.8 and reviews >= 10 and has_phone:
        return "✅ Bueno"
    return "❄️ Frío"

def get_wa_link(row, country_name):
    """Genera un link de WhatsApp para el lead."""
    tel = str(row.get('telefono', ''))
    num = "".join(filter(str.isdigit, tel))
    if not num or len(num) < 7:
        return ""
    
    pref = COUNTRY_CODES.get(country_name, "")
    if pref and not num.startswith(pref):
        num = pref + num
        
    tipo = row.get('tipo', 'negocio')
    rating = row.get('rating', 'N/A')
    nombre = row.get('nombre', 'propietario')
    
    msg = (f"Hola {nombre}, vi tu negocio de {tipo} en Google Maps. "
           f"Tienes una puntuación de {rating} y me gustaría comentarte algo. ¿Hablamos?")
    
    return f"https://wa.me/{num}?text={urllib.parse.quote(msg)}"

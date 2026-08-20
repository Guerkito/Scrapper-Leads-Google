import urllib.parse
import sqlite3
import pandas as pd
import streamlit as st
from loguru import logger
from db import DB_PATH, open_conn
from services.phone_utils import phone_digits

@st.cache_data(ttl=30, show_spinner=False)
def load_all_leads():
    """Carga todos los leads desde la base de datos de forma segura."""
    try:
        conn = open_conn()
        try:
            df = pd.read_sql_query(
                """
                SELECT
                    l.*,
                    COALESCE((
                        SELECT GROUP_CONCAT(DISTINCT o.product_key)
                        FROM lead_opportunities o WHERE o.lead_id = l.id
                    ), '') AS product_keys,
                    COALESCE((
                        SELECT GROUP_CONCAT(DISTINCT o.product_label)
                        FROM lead_opportunities o WHERE o.lead_id = l.id
                    ), '') AS productos_objetivo,
                    COALESCE((
                        SELECT GROUP_CONCAT(DISTINCT o.segment_label)
                        FROM lead_opportunities o WHERE o.lead_id = l.id
                    ), '') AS segmentos_objetivo,
                    COALESCE((
                        SELECT o.product_label FROM lead_opportunities o
                        WHERE o.lead_id = l.id
                        ORDER BY o.fit_score DESC, o.updated_at DESC LIMIT 1
                    ), '') AS producto_principal,
                    COALESCE((
                        SELECT o.product_key FROM lead_opportunities o
                        WHERE o.lead_id = l.id
                        ORDER BY o.fit_score DESC, o.updated_at DESC LIMIT 1
                    ), '') AS campaign_key_principal,
                    COALESCE((
                        SELECT o.segment_label FROM lead_opportunities o
                        WHERE o.lead_id = l.id
                        ORDER BY o.fit_score DESC, o.updated_at DESC LIMIT 1
                    ), '') AS segmento_principal,
                    COALESCE((
                        SELECT o.fit_score FROM lead_opportunities o
                        WHERE o.lead_id = l.id
                        ORDER BY o.fit_score DESC, o.updated_at DESC LIMIT 1
                    ), 0) AS fit_score,
                    COALESCE((
                        SELECT o.fit_reason FROM lead_opportunities o
                        WHERE o.lead_id = l.id
                        ORDER BY o.fit_score DESC, o.updated_at DESC LIMIT 1
                    ), '') AS motivo_afinidad,
                    COALESCE((
                        SELECT o.pitch FROM lead_opportunities o
                        WHERE o.lead_id = l.id
                        ORDER BY o.fit_score DESC, o.updated_at DESC LIMIT 1
                    ), '') AS pitch_sugerido,
                    COALESCE((
                        SELECT o.decision_roles FROM lead_opportunities o
                        WHERE o.lead_id = l.id
                        ORDER BY o.fit_score DESC, o.updated_at DESC LIMIT 1
                    ), '') AS decisor_objetivo
                FROM leads l
                """,
                conn,
            )
            return df
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error cargando leads: {e}")
        return pd.DataFrame()


def invalidate_leads_cache():
    """Invalida la caché tras inserts/updates relevantes."""
    try:
        load_all_leads.clear()
    except Exception:
        pass

def get_score(row):
    """Lead scoring automático basado en rating, reseñas y teléfono."""
    try:
        raw_rating = row.get('rating', 0)
        rating_str = str(raw_rating if pd.notna(raw_rating) else 0).split('/')[0].strip().replace(',', '.')
        rating = float(rating_str)
        reviews_str = "".join(filter(str.isdigit, str(row.get('reseñas', '0'))))
        reviews = int(reviews_str or 0)
    except (ValueError, IndexError, AttributeError):
        return "Frío"
    
    has_phone = bool(row.get('telefono') and str(row.get('telefono')) not in ('N/A', '', 'None'))
    
    if rating >= 4.3 and reviews >= 30 and has_phone:
        return "Oro"
    if rating >= 3.8 and reviews >= 10 and has_phone:
        return "Bueno"
    return "Frío"

def get_wa_link(row, country_name):
    """Genera un link de WhatsApp para el lead."""
    lead_country = row.get('pais')
    if pd.isna(lead_country) or not str(lead_country).strip():
        lead_country = country_name
    phone = row.get('telefono_e164')
    if pd.isna(phone) or not str(phone).strip():
        phone = row.get('telefono')
    num = phone_digits(phone, lead_country)
    if not num:
        return ""
        
    tipo = row.get('tipo', 'negocio')
    nicho = row.get('nicho', 'negocio')
    rating = row.get('rating', 'N/A')
    nombre = row.get('nombre', 'propietario')
    product = row.get('producto_principal')
    pitch = row.get('pitch_sugerido')

    if pd.notna(product) and str(product).strip():
        benefit = str(pitch).strip() if pd.notna(pitch) and str(pitch).strip() else "mejorar su operación"
        msg = (
            f"Hola, soy de ONYX. Vi a {nombre} y quisiera presentarles {product}: "
            f"{benefit} ¿Con quién podría revisar esta solución?"
        )
        return f"https://wa.me/{num}?text={urllib.parse.quote(msg)}"

    if nicho and nicho != 'General':
        msg = (f"Hola {nombre}, vi tu negocio de {nicho} en Google Maps. "
               f"Tienes una puntuación de {rating} y me gustaría comentarte algo sobre tu presencia digital. ¿Hablamos?")
    else:
        msg = (f"Hola {nombre}, vi tu negocio de {tipo} en Google Maps. "
               f"Tienes una puntuación de {rating} y me gustaría comentarte algo. ¿Hablamos?")
    
    return f"https://wa.me/{num}?text={urllib.parse.quote(msg)}"

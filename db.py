import sqlite3
import datetime
import os
import json

from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.getcwd(), "data", "leads.db"))
DB_DIR = os.path.dirname(DB_PATH)
if DB_DIR and not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)


def open_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_db():
    conn = open_conn()
    conn.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        ciudad TEXT,
        departamento TEXT,
        direccion TEXT,
        telefono TEXT,
        email TEXT,
        sitio_web TEXT,
        tiene_web BOOLEAN DEFAULT FALSE,
        rating REAL,
        reseñas INTEGER DEFAULT 0,
        maps_url TEXT,
        nicho TEXT,
        sector TEXT,
        tipo TEXT CHECK(tipo IN ('B2B', 'B2C')),
        fuente TEXT,
        fuentes_encontrado TEXT,
        nit TEXT,
        representante_legal TEXT,
        ciiu TEXT,
        calificacion TEXT CHECK(calificacion IN ('oro', 'bueno', 'frio')),
        estado TEXT DEFAULT 'Nuevo',
        estado_contacto TEXT DEFAULT 'sin_contactar',
        notas TEXT,
        ultima_interaccion TEXT,
        bot_pausado INTEGER DEFAULT 0,
        whatsapp_id TEXT,
        pais TEXT,
        zona TEXT,
        historial_mensajes TEXT,
        lat REAL,
        lng REAL,
        fecha_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fecha_ultimo_contacto TIMESTAMP,
        raw_data TEXT,
        UNIQUE(nombre, ciudad))''')
    
    # Migración de columnas nuevas
    cursor = conn.execute("PRAGMA table_info(leads)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    
    new_cols = {
        "departamento": "TEXT", "direccion": "TEXT", "email": "TEXT", "sitio_web": "TEXT",
        "tiene_web": "BOOLEAN DEFAULT FALSE", "fuentes_encontrado": "TEXT", "nit": "TEXT",
        "representante_legal": "TEXT", "ciiu": "TEXT", "calificacion": "TEXT",
        "estado": "TEXT DEFAULT 'Nuevo'", "estado_contacto": "TEXT DEFAULT 'sin_contactar'",
        "notas": "TEXT", "ultima_interaccion": "TEXT", "bot_pausado": "INTEGER DEFAULT 0",
        "whatsapp_id": "TEXT", "pais": "TEXT", "zona": "TEXT", "historial_mensajes": "TEXT",
        "fecha_captura": "TIMESTAMP", "fecha_ultimo_contacto": "TIMESTAMP",
        "raw_data": "TEXT", "sector": "TEXT",
        "instagram": "TEXT", "facebook": "TEXT", "linkedin_empresa": "TEXT",
        "pixel_fb": "BOOLEAN DEFAULT FALSE", "pixel_google": "BOOLEAN DEFAULT FALSE",
        "decisor": "TEXT", "verificado": "BOOLEAN DEFAULT FALSE",
        "reseñas": "INTEGER DEFAULT 0", "maps_url": "TEXT"
    }
    
    for col, type_def in new_cols.items():
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {type_def}")

    # Crear índices después de asegurar que las columnas existen
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ciudad ON leads(ciudad)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nicho ON leads(nicho)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nit ON leads(nit)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_calificacion ON leads(calificacion)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_estado ON leads(estado)")

    conn.execute('''CREATE TABLE IF NOT EXISTS bot_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        mensaje TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        ciudad TEXT,
        pais TEXT,
        nicho TEXT,
        zona TEXT,
        leads_nuevos INTEGER DEFAULT 0,
        leads_duplicados INTEGER DEFAULT 0
    )''')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_fecha ON search_history(fecha)")

    conn.execute('''CREATE TABLE IF NOT EXISTS search_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE,
        nicho TEXT,
        pais TEXT,
        ciudades TEXT,
        fuentes TEXT,
        limit_sel INTEGER,
        deep_scan BOOLEAN,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_nombre TEXT,
        cliente_email TEXT,
        paquete TEXT,
        sector TEXT,
        instrucciones TEXT,
        estado TEXT DEFAULT 'Pendiente',
        fecha_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()


def save_lead(lead, conn):
    """
    Inserta o enriquece un lead. Maneja la fusión de fuentes como lista JSON.
    """
    if hasattr(lead, 'nombre'): # Objeto Lead
        nombre = lead.nombre
        ciudad = lead.ciudad
        
        # 1. Obtener datos existentes para el merge
        cursor = conn.execute("SELECT fuentes_encontrado FROM leads WHERE nombre = ? AND ciudad = ?", (nombre, ciudad))
        row = cursor.fetchone()
        
        fuentes_lista = []
        if row and row[0]:
            try:
                fuentes_lista = json.loads(row[0])
            except:
                fuentes_lista = [row[0]] if row[0] else []
        
        if lead.fuente not in fuentes_lista:
            fuentes_lista.append(lead.fuente)
        
        fuentes_json = json.dumps(fuentes_lista)
        raw_json = json.dumps(lead.raw_data)
        try:
            conn.execute(
                '''INSERT INTO leads
                   (nombre, ciudad, direccion, telefono, email, sitio_web, tiene_web,
                    rating, reseñas, maps_url, nicho, sector, tipo, fuente, fuentes_encontrado, nit,
                    calificacion, lat, lng, instagram, facebook, linkedin_empresa,
                    pixel_fb, pixel_google, decisor, verificado, raw_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(nombre, ciudad) DO UPDATE SET
                    telefono = COALESCE(NULLIF(NULLIF(excluded.telefono, 'N/A'), ''), leads.telefono),
                    email = COALESCE(NULLIF(excluded.email, ''), leads.email),
                    sitio_web = COALESCE(NULLIF(NULLIF(excluded.sitio_web, 'N/A'), ''), leads.sitio_web),
                    nit = COALESCE(NULLIF(excluded.nit, ''), leads.nit),
                    rating = MAX(COALESCE(leads.rating, 0), COALESCE(excluded.rating, 0)),
                    reseñas = MAX(COALESCE(leads.reseñas, 0), COALESCE(excluded.reseñas, 0)),
                    maps_url = COALESCE(NULLIF(excluded.maps_url, ''), leads.maps_url),
                    instagram = COALESCE(NULLIF(excluded.instagram, ''), leads.instagram),
                    facebook = COALESCE(NULLIF(excluded.facebook, ''), leads.facebook),
                    linkedin_empresa = COALESCE(NULLIF(excluded.linkedin_empresa, ''), leads.linkedin_empresa),
                    pixel_fb = CASE WHEN excluded.pixel_fb THEN 1 ELSE leads.pixel_fb END,
                    pixel_google = CASE WHEN excluded.pixel_google THEN 1 ELSE leads.pixel_google END,
                    decisor = COALESCE(NULLIF(excluded.decisor, ''), leads.decisor),
                    fuentes_encontrado = excluded.fuentes_encontrado,
                    raw_data = excluded.raw_data
                ''',
                (
                    lead.nombre, lead.ciudad, lead.direccion, lead.telefono,
                    lead.email, lead.sitio_web, lead.tiene_web, lead.rating,
                    getattr(lead, 'reseñas', 0), getattr(lead, 'maps_url', None),
                    lead.nicho, lead.sector, lead.tipo, lead.fuente, fuentes_json,
                    lead.nit, lead.calificacion, lead.lat, lead.lng,
                    lead.instagram, lead.facebook, lead.linkedin_empresa,
                    lead.pixel_fb, lead.pixel_google, lead.decisor, lead.verificado, raw_json
                )
            )
            return True
        except Exception as e:
            print(f"❌ ERROR save_lead UPSERT: {e}")
            return False
    else: # Fallback para compatibilidad con formato dict (usado en scraper.py)
        try:
            nombre = lead.get('Nombre')
            ciudad = lead.get('Ciudad')
            
            # Obtener datos existentes para merge de fuentes
            cursor = conn.execute("SELECT fuentes_encontrado FROM leads WHERE nombre = ? AND ciudad = ?", (nombre, ciudad))
            row = cursor.fetchone()
            
            fuentes_lista = []
            if row and row[0]:
                try:
                    fuentes_lista = json.loads(row[0])
                except:
                    fuentes_lista = [row[0]] if row[0] else []
            
            fuente = lead.get('Fuente', 'google_maps')
            if fuente not in fuentes_lista:
                fuentes_lista.append(fuente)
            
            fuentes_json = json.dumps(fuentes_lista)
            
            # Mapeo de campos
            rating_val = lead.get('Rating')
            if isinstance(rating_val, str) and '/' in rating_val:
                try:
                    rating_val = float(rating_val.split('/')[0].strip())
                except:
                    rating_val = None
            
            resenas_val = lead.get('Reseñas', 0)
            if isinstance(resenas_val, str):
                resenas_val = int("".join(filter(str.isdigit, resenas_val)) or 0)

            conn.execute(
                '''INSERT INTO leads
                   (nombre, ciudad, telefono, rating, reseñas, nicho, tipo, zona, pais, lat, lng, 
                    sitio_web, tiene_web, maps_url, estado, notas, fuentes_encontrado, fecha_captura)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(nombre, ciudad) DO UPDATE SET
                    telefono = COALESCE(NULLIF(NULLIF(excluded.telefono, 'N/A'), ''), leads.telefono),
                    rating = MAX(COALESCE(leads.rating, 0), COALESCE(excluded.rating, 0)),
                    reseñas = MAX(COALESCE(leads.reseñas, 0), COALESCE(excluded.reseñas, 0)),
                    sitio_web = COALESCE(NULLIF(NULLIF(excluded.sitio_web, 'N/A'), ''), leads.sitio_web),
                    tiene_web = CASE WHEN excluded.tiene_web THEN 1 ELSE leads.tiene_web END,
                    maps_url = COALESCE(NULLIF(excluded.maps_url, ''), leads.maps_url),
                    fuentes_encontrado = excluded.fuentes_encontrado
                ''',
                (
                    nombre, ciudad, lead.get('Teléfono'), rating_val, resenas_val,
                    lead.get('Nicho'), lead.get('Tipo'), lead.get('Zona'), lead.get('Pais'),
                    lead.get('Lat'), lead.get('Lng'), lead.get('Web'), 
                    bool(lead.get('Web') and lead.get('Web') != "Sin sitio web"),
                    lead.get('Maps_URL'), lead.get('Estado', 'Nuevo'), lead.get('Notas'),
                    fuentes_json
                )
            )
            return True
        except Exception as e:
            print(f"❌ ERROR save_lead Dict: {e}")
            return False



def load_known_identifiers(ciudad: str, conn) -> tuple[set, set]:
    """Carga identificadores conocidos (nombres y Place IDs)."""
    nombres = {r[0].lower() for r in conn.execute("SELECT nombre FROM leads WHERE ciudad = ?", (ciudad,)).fetchall() if r[0]}
    
    # Extraer CIDs de las maps_url existentes
    cids = set()
    cursor = conn.execute("SELECT maps_url FROM leads WHERE maps_url IS NOT NULL")
    for row in cursor.fetchall():
        url = row[0]
        # El CID suele estar después de !1s y tiene el formato 0xHEX:0xHEX
        import re
        m = re.search(r'!1s(0x[0-9a-fA-F]+:[0-9a-fA-F]+)', url)
        if m:
            cids.add(m.group(1))
            
    return nombres, cids


def save_search_history(ciudad, pais, nicho, zona, leads_nuevos, leads_duplicados, conn):
    """Historial de búsqueda."""
    conn.execute(
        "INSERT INTO search_history (fecha, ciudad, pais, nicho, zona, leads_nuevos, leads_duplicados) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), ciudad, pais, nicho, zona, leads_nuevos, leads_duplicados)
    )
    conn.commit()

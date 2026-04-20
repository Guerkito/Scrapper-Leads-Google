import sqlite3
import datetime
import os

if os.path.exists("/data"):
    DB_DIR = "/data"
else:
    DB_DIR = os.path.join(os.getcwd(), "data")
    os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "leads.db")


def open_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_db():
    conn = open_conn()
    conn.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, telefono TEXT, rating TEXT, reseñas TEXT,
        tipo TEXT, lat REAL, lng REAL, zona TEXT, ciudad TEXT, pais TEXT,
        nicho TEXT, fecha TEXT, web TEXT, maps_url TEXT,
        estado TEXT DEFAULT 'Nuevo', notas TEXT,
        ultima_interaccion TEXT,
        bot_pausado INTEGER DEFAULT 0,
        tipo_contacto TEXT,
        UNIQUE(nombre, ciudad))''')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_estado ON leads(estado)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_nicho ON leads(nicho)")

    # Migración de columnas nuevas si la DB ya existe
    cursor = conn.execute("PRAGMA table_info(leads)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    
    new_cols = {
        "maps_url": "TEXT",
        "ultima_interaccion": "TEXT",
        "bot_pausado": "INTEGER DEFAULT 0",
        "tipo_contacto": "TEXT",
        "historial_mensajes": "TEXT"
    }
    
    for col, type_def in new_cols.items():
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {type_def}")
    
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

    cursor = conn.execute("PRAGMA table_info(leads)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "maps_url" not in existing_cols:
        conn.execute("ALTER TABLE leads ADD COLUMN maps_url TEXT")
    conn.commit()
    conn.close()


def save_lead(lead, conn):
    """Inserta un lead. Retorna True si fue nuevo, False si era duplicado."""
    cursor = conn.execute(
        '''INSERT OR IGNORE INTO leads
           (nombre, telefono, rating, reseñas, tipo, lat, lng, zona, ciudad, pais,
            nicho, fecha, web, maps_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            lead['Nombre'], lead['Teléfono'], lead['Rating'], lead['Reseñas'],
            lead['Tipo'], lead.get('Lat'), lead.get('Lng'), lead['Zona'],
            lead['Ciudad'], lead['Pais'], lead['Nicho'],
            datetime.datetime.now().strftime("%Y-%m-%d"),
            lead.get('Web'), lead.get('Maps_URL'),
        ),
    )
    return cursor.rowcount > 0  # True = nuevo, False = duplicado


def load_known_identifiers(ciudad: str, conn) -> tuple[set, set]:
    """
    Carga los identificadores ya conocidos para una ciudad.
    Retorna (set_nombres_lower, set_place_ids).
    Se llama UNA vez al inicio del escaneo para hacer pre-filtrado sin tocar la DB.
    """
    nombres = {
        r[0].lower()
        for r in conn.execute(
            "SELECT nombre FROM leads WHERE ciudad = ?", (ciudad,)
        ).fetchall()
        if r[0]
    }
    place_ids = {
        r[0]
        for r in conn.execute(
            "SELECT maps_url FROM leads WHERE maps_url IS NOT NULL AND maps_url != ''"
        ).fetchall()
        if r[0]
    }
    return nombres, place_ids


def save_search_history(ciudad, pais, nicho, zona, leads_nuevos, leads_duplicados, conn):
    """Guarda un registro en el historial de búsquedas."""
    conn.execute(
        '''INSERT INTO search_history (fecha, ciudad, pais, nicho, zona, leads_nuevos, leads_duplicados)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            ciudad, pais, nicho, zona, leads_nuevos, leads_duplicados,
        ),
    )
    conn.commit()

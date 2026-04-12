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
        UNIQUE(nombre, ciudad))''')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_estado ON leads(estado)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_nicho ON leads(nicho)")
    cursor = conn.execute("PRAGMA table_info(leads)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "maps_url" not in existing_cols:
        conn.execute("ALTER TABLE leads ADD COLUMN maps_url TEXT")
    conn.commit()
    conn.close()


def save_lead(lead, conn):
    """Inserta un lead. El caller es responsable del commit."""
    conn.execute(
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

import sqlite3
import datetime
import os
import json
import re
from loguru import logger

from config import DB_PATH
from services.phone_utils import normalize_phone

DB_DIR = os.path.dirname(DB_PATH)
if DB_DIR and not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)


def clean_phone_number(phone: str) -> str:
    """Normaliza y limpia un número de teléfono eliminando caracteres no deseados,
    bidi markers, saltos de línea y notación científica de floats.
    """
    if not phone or not isinstance(phone, str):
        return "N/A"
    phone_clean = phone.strip()
    if phone_clean.lower() in ("nan", "n/a", "none", "", "null"):
        return "N/A"

    # Si termina en .0 (muy común si se importó de un float de Pandas/Excel), quitarlo
    if phone_clean.endswith(".0"):
        phone_clean = phone_clean[:-2]

    # Si viene en notación científica, p.ej. 3.11e+09
    if "e+" in phone_clean.lower() or "e-" in phone_clean.lower():
        try:
            phone_clean = str(int(float(phone_clean)))
        except ValueError:
            pass

    # Reemplazar saltos de línea por espacios
    phone_clean = phone_clean.replace('\n', ' ').replace('\r', ' ')
    # Eliminar marcadores Unicode bidi y caracteres especiales no deseados (como \ue0b0)
    phone_clean = re.sub(r'[\u200e\u200f\u202a\u202b\u202c\ue0b0]', '', phone_clean)

    # Extraer el patrón del teléfono (admitir +, dígitos, espacios, guiones y paréntesis)
    m = re.search(r"(\+?[\d\s\(\)-]{7,})", phone_clean)
    if m:
        val = m.group(1).strip()
        # Verificar que tenga al menos 7 dígitos para que sea válido
        if len(re.sub(r'[^\d]', '', val)) >= 7:
            return val

    # Si no macheó pero tras remover no-dígitos quedan al menos 7 dígitos, limpiar conservando el formato
    only_digits = re.sub(r'[^\d]', '', phone_clean)
    if len(only_digits) >= 7:
        return re.sub(r'[^\d\s\(\)+-]', '', phone_clean).strip()

    return "N/A"


FAMOUS_BRANDS = {
    "adidas": "https://www.adidas.co",
    "nike": "https://www.nike.com.co",
    "puma": "https://co.puma.com",
    "mcdonald": "https://www.mcdonalds.com.co",
    "mcdonalds": "https://www.mcdonalds.com.co",
    "starbucks": "https://www.starbucks.com.co",
    "burger king": "https://www.burgerking.com.co",
    "subway": "https://www.subway.com.co",
    "crepes & waffles": "https://crepesywaffles.com",
    "crepes and waffles": "https://crepesywaffles.com",
    "el corral": "https://www.elcorral.com",
    "exito": "https://www.exito.com",
    "carulla": "https://www.carulla.com",
    "tiendas jumbo": "https://www.tiendasjumbo.co",
    "jumbo": "https://www.tiendasjumbo.co",
    "olimpica": "https://www.olimpica.com",
    "alkosto": "https://www.alkosto.com",
    "decathlon": "https://www.decathlon.com.co",
    "falabella": "https://www.falabella.com.co",
    "zara": "https://www.zara.com/co/",
    "h&m": "https://co.hm.com",
    "hm.com": "https://co.hm.com",
    "arturo calle": "https://www.arturocalle.com",
    "tostao": "https://tostao.com",
    "juan valdez": "https://juanvaldezcafe.com",
    "bogota beer company": "https://www.bbccerveceria.com",
    "bbc cerveceria": "https://www.bbccerveceria.com",
    "frisby": "https://frisby.com.co",
    "farmatodo": "https://www.farmatodo.com.co",
    "cafam": "https://www.drogueriascafam.com.co",
    "cruz verde": "https://www.cruzverde.com.co"
}


def resolve_corporate_website(nombre: str) -> str | None:
    """Verifica si el nombre del negocio pertenece a una gran franquicia o marca
    y retorna su sitio web corporativo de ser así.
    """
    if not nombre or not isinstance(nombre, str):
        return None
    name_lower = nombre.lower()
    for brand, web in FAMOUS_BRANDS.items():
        if re.search(rf"\b{re.escape(brand)}\b", name_lower):
            return web
    return None


class _ClosingConnection(sqlite3.Connection):
    """Conexión que cierra sola al salir del `with`.

    ``sqlite3.Connection.__exit__`` hace commit/rollback pero NO cierra la
    conexión; el patrón ``with open_conn() as conn:`` dejaba conexiones
    abiertas hasta el GC. Esta subclase las cierra al salir del bloque.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        try:
            self.close()
        except sqlite3.Error:
            pass
        return False


def open_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False, factory=_ClosingConnection)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


SCHEMA_VERSION = 11


def _get_schema_version(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)")
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    return row[0] if row else 0


def _set_schema_version(conn, version):
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


def _migrate(conn, current_version):
    """Aplica migraciones idempotentes solo si la versión es menor que la actual."""
    cursor = conn.execute("PRAGMA table_info(leads)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    if current_version < 1:
        # v1: columnas históricas que no estaban en el CREATE original
        legacy_cols = {
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
            "reseñas": "INTEGER DEFAULT 0", "maps_url": "TEXT",
        }
        for col, type_def in legacy_cols.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {type_def}")
                existing_cols.add(col)

    if current_version < 2:
        # v2: columna place_id indexada (sustituye al regex sobre maps_url)
        if "place_id" not in existing_cols:
            conn.execute("ALTER TABLE leads ADD COLUMN place_id TEXT")
            existing_cols.add("place_id")
        # Backfill: extraer place_id de maps_url existente
        import re as _re
        rows = conn.execute(
            "SELECT id, maps_url FROM leads WHERE place_id IS NULL AND maps_url IS NOT NULL"
        ).fetchall()
        for lead_id, url in rows:
            m = _re.search(r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)", url or "")
            if m:
                conn.execute("UPDATE leads SET place_id = ? WHERE id = ?", (m.group(1), lead_id))

    if current_version < 3:
        # v3: identidad basada en place_id (clave estable de Maps).
        _consolidate_place_id_duplicates(conn)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_place_id "
            "ON leads(place_id) WHERE place_id IS NOT NULL"
        )

    if current_version < 4:
        # v4: dos negocios reales con mismo nombre+ciudad pero distinto place_id
        # deben coexistir. Eliminamos UNIQUE(nombre, ciudad) del CREATE original
        # y lo sustituimos por un índice único parcial (solo cuando place_id IS NULL).
        _rebuild_table_without_unique_nombre_ciudad(conn)
        # Re-crear los índices que se perdieron al recrear la tabla
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_place_id "
            "ON leads(place_id) WHERE place_id IS NOT NULL"
        )
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_nombre_ciudad_no_pid "
                "ON leads(nombre, ciudad) WHERE place_id IS NULL"
            )
        except sqlite3.IntegrityError:
            logger.warning("Duplicados (nombre, ciudad) sin place_id; fusionando filas antes del índice v4.")
            _consolidate_identity_duplicates_legacy(conn)
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_nombre_ciudad_no_pid "
                "ON leads(nombre, ciudad) WHERE place_id IS NULL"
            )

    if current_version < 5:
        # v5: regex de place_id corregida (captura el segundo `0x` completo).
        # Re-extrae el place_id en cada row para reflejar la captura correcta.
        # Los rows existentes pueden quedar con place_ids diferentes — eso es esperado:
        # negocios que la regex anterior colapsaba erróneamente ahora quedan separados.
        import re as _re
        rows = conn.execute("SELECT id, maps_url FROM leads WHERE maps_url IS NOT NULL").fetchall()
        for lead_id, url in rows:
            m = _re.search(r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)", url or "")
            new_pid = m.group(1) if m else None
            try:
                conn.execute("UPDATE leads SET place_id = ? WHERE id = ?", (new_pid, lead_id))
            except sqlite3.IntegrityError:
                # Si un place_id corregido choca con otro row existente, dejamos NULL
                # y caerá en el fallback (nombre, ciudad). Caso raro.
                conn.execute("UPDATE leads SET place_id = NULL WHERE id = ?", (lead_id,))

    if current_version < 6:
        # v6: identidad geografica completa, telefonos E.164 y perfiles de terceros.
        for col, type_def in {
            "telefono_e164": "TEXT",
            "perfil_url": "TEXT",
        }.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {type_def}")
                existing_cols.add(col)

        # Recuperar geografia solo cuando el nombre de ciudad es inequivoco.
        from geo_data import GEO_DATA
        city_locations = {}
        for country, regions in GEO_DATA.items():
            for department, cities in regions.items():
                for city in cities:
                    city_locations.setdefault(city.casefold(), set()).add((country, department))
        for city_key, locations in city_locations.items():
            if len(locations) != 1:
                continue
            country, department = next(iter(locations))
            conn.execute(
                """
                UPDATE leads SET
                    pais = COALESCE(NULLIF(trim(pais), ''), ?),
                    departamento = COALESCE(NULLIF(trim(departamento), ''), ?)
                WHERE lower(trim(COALESCE(ciudad, ''))) = ?
                """,
                (country, department, city_key),
            )

        # El indice anterior mezclaba ciudades homonimas de paises diferentes.
        conn.execute("DROP INDEX IF EXISTS idx_unique_nombre_ciudad_no_pid")
        _consolidate_normalized_identity_duplicates(conn)
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_identity_no_pid ON leads("
                "lower(trim(nombre)), lower(trim(COALESCE(ciudad, ''))), "
                "lower(trim(COALESCE(pais, '')))) WHERE place_id IS NULL"
            )
        except sqlite3.IntegrityError:
            logger.warning("Duplicados de identidad tras migración v6; fusionando antes del índice.")
            _consolidate_normalized_identity_duplicates(conn)
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_identity_no_pid ON leads("
                "lower(trim(nombre)), lower(trim(COALESCE(ciudad, ''))), "
                "lower(trim(COALESCE(pais, '')))) WHERE place_id IS NULL"
            )

        rows = conn.execute(
            "SELECT id, telefono, pais FROM leads "
            "WHERE telefono IS NOT NULL AND telefono NOT IN ('', 'N/A')"
        ).fetchall()
        updates = []
        for lead_id, phone, country in rows:
            normalized = normalize_phone(phone, country)
            if normalized:
                updates.append((normalized, lead_id))
        if updates:
            conn.executemany(
                "UPDATE leads SET telefono_e164 = ? WHERE id = ?", updates
            )

    if current_version < 7:
        # v7 agrega oportunidades por producto en una tabla separada durante init_db.
        # No se añaden columnas al lead: un negocio puede servir a varias campañas.
        pass

    if current_version < 8:
        # v8: atribución de leads a la misión/búsqueda que los capturó.
        if "mision_id" not in existing_cols:
            conn.execute("ALTER TABLE leads ADD COLUMN mision_id TEXT")
            existing_cols.add("mision_id")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_mision ON leads(mision_id)")

    if current_version < 9:
        # v9: seguimiento automático de correos fríos.
        if "follow_ups_sent" not in existing_cols:
            conn.execute("ALTER TABLE leads ADD COLUMN follow_ups_sent INTEGER DEFAULT 0")
            existing_cols.add("follow_ups_sent")

    if current_version < 10:
        # v10: decisor a nivel persona (nombre, cargo y LinkedIn verificable).
        for col, type_def in {
            "decisor_nombre": "TEXT",
            "decisor_cargo": "TEXT",
            "decisor_linkedin": "TEXT",
        }.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {type_def}")
                existing_cols.add(col)

    if current_version < 11:
        # v11: reunión confirmada por la agenda (Cal.com).
        for col, type_def in {
            "reunion_at": "TEXT",
            "reunion_url": "TEXT",
        }.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {type_def}")
                existing_cols.add(col)


def _rebuild_table_without_unique_nombre_ciudad(conn):
    """Recrea la tabla `leads` eliminando el UNIQUE(nombre, ciudad) del CREATE original.

    SQLite no permite ALTER TABLE ... DROP CONSTRAINT, así que copiamos a una tabla nueva.
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(leads)").fetchall()]
    cols_csv = ",".join(cols)

    conn.execute("DROP TABLE IF EXISTS leads_new")
    conn.execute('''CREATE TABLE leads_new (
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
        place_id TEXT,
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
        perfil_url TEXT,
        telefono_e164 TEXT,
        instagram TEXT,
        facebook TEXT,
        linkedin_empresa TEXT,
        pixel_fb BOOLEAN DEFAULT FALSE,
        pixel_google BOOLEAN DEFAULT FALSE,
        decisor TEXT,
        verificado BOOLEAN DEFAULT FALSE
    )''')

    # Copiar solo las columnas que existen en ambos lados
    new_cols = [r[1] for r in conn.execute("PRAGMA table_info(leads_new)").fetchall()]
    common = [c for c in cols if c in new_cols]
    common_csv = ",".join(common)
    conn.execute(f"INSERT INTO leads_new ({common_csv}) SELECT {common_csv} FROM leads")
    conn.execute("DROP TABLE leads")
    conn.execute("ALTER TABLE leads_new RENAME TO leads")


def _consolidate_place_id_duplicates(conn):
    """Fusiona rows con el mismo place_id en el row de id menor (primero capturado).

    Para cada campo: si el row destino está vacío, copia el del duplicado.
    Las listas (`fuentes_encontrado`) se unen por unión.
    """
    groups = conn.execute(
        """
        SELECT place_id, GROUP_CONCAT(id) FROM leads
        WHERE place_id IS NOT NULL
        GROUP BY place_id HAVING COUNT(*) > 1
        """
    ).fetchall()
    if not groups:
        return

    # Columnas a fusionar (excluyendo id, place_id y la PK)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(leads)").fetchall()]
    mergeable = [c for c in cols if c not in ("id", "place_id")]

    for _pid, ids_csv in groups:
        ids = sorted(int(x) for x in ids_csv.split(","))
        keep_id, drop_ids = ids[0], ids[1:]

        keep = dict(zip(
            cols,
            conn.execute(f"SELECT {','.join(cols)} FROM leads WHERE id = ?", (keep_id,)).fetchone(),
        ))

        for did in drop_ids:
            other = dict(zip(
                cols,
                conn.execute(f"SELECT {','.join(cols)} FROM leads WHERE id = ?", (did,)).fetchone(),
            ))
            for c in mergeable:
                if c == "fuentes_encontrado":
                    a, b = keep.get(c), other.get(c)
                    try:
                        la = json.loads(a) if a else []
                        lb = json.loads(b) if b else []
                    except Exception:
                        la, lb = ([a] if a else []), ([b] if b else [])
                    merged = list(dict.fromkeys(la + lb))  # preserva orden, sin duplicados
                    keep[c] = json.dumps(merged)
                elif not keep.get(c) and other.get(c):
                    keep[c] = other[c]

        # Persistir el row consolidado y borrar los duplicados
        set_clause = ",".join(f"{c} = ?" for c in mergeable)
        conn.execute(
            f"UPDATE leads SET {set_clause} WHERE id = ?",
            [keep[c] for c in mergeable] + [keep_id],
        )
        conn.executemany(
            "DELETE FROM leads WHERE id = ?",
            [(d,) for d in drop_ids],
        )


def _consolidate_identity_duplicates_legacy(conn):
    """Fusiona duplicados exactos de (nombre, ciudad) sin place_id (bases pre-v4)."""
    groups = conn.execute(
        """
        SELECT GROUP_CONCAT(id) FROM leads
        WHERE place_id IS NULL
        GROUP BY lower(trim(nombre)), lower(trim(COALESCE(ciudad, '')))
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    columns = [row[1] for row in conn.execute("PRAGMA table_info(leads)")]
    for (ids_csv,) in groups:
        ids = sorted(int(value) for value in ids_csv.split(","))
        keep_id = ids[0]
        keep_row = conn.execute("SELECT * FROM leads WHERE id = ?", (keep_id,)).fetchone()
        merged = dict(zip(columns, keep_row))
        for drop_id in ids[1:]:
            row = conn.execute("SELECT * FROM leads WHERE id = ?", (drop_id,)).fetchone()
            other = dict(zip(columns, row))
            for column in columns:
                if column in {"id", "place_id"}:
                    continue
                if column == "fuentes_encontrado":
                    merged[column] = json.dumps(list(dict.fromkeys(
                        _json_list(merged.get(column)) + _json_list(other.get(column))
                    )), ensure_ascii=False)
                elif column in {"rating", "reseñas"}:
                    merged[column] = max(merged.get(column) or 0, other.get(column) or 0)
                elif not _meaningful(merged.get(column)) and _meaningful(other.get(column)):
                    merged[column] = other[column]
        update_columns = [column for column in columns if column != "id"]
        conn.execute(
            f"UPDATE leads SET {','.join(f'{column} = ?' for column in update_columns)} WHERE id = ?",
            [merged.get(column) for column in update_columns] + [keep_id],
        )
        conn.executemany("DELETE FROM leads WHERE id = ?", [(value,) for value in ids[1:]])


def _consolidate_normalized_identity_duplicates(conn):
    """Fusiona variantes de mayusculas/espacios antes de crear el indice v6."""
    groups = conn.execute(
        """
        SELECT GROUP_CONCAT(id) FROM leads
        WHERE place_id IS NULL
        GROUP BY lower(trim(nombre)), lower(trim(COALESCE(ciudad, ''))),
                 lower(trim(COALESCE(pais, '')))
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    columns = [row[1] for row in conn.execute("PRAGMA table_info(leads)")]
    for (ids_csv,) in groups:
        ids = sorted(int(value) for value in ids_csv.split(","))
        keep_id = ids[0]
        keep_row = conn.execute("SELECT * FROM leads WHERE id = ?", (keep_id,)).fetchone()
        merged = dict(zip(columns, keep_row))
        for drop_id in ids[1:]:
            row = conn.execute("SELECT * FROM leads WHERE id = ?", (drop_id,)).fetchone()
            other = dict(zip(columns, row))
            for column in columns:
                if column in {"id", "place_id"}:
                    continue
                if column == "fuentes_encontrado":
                    merged[column] = json.dumps(list(dict.fromkeys(
                        _json_list(merged.get(column)) + _json_list(other.get(column))
                    )), ensure_ascii=False)
                elif column == "raw_data":
                    merged[column] = _merge_raw_data(
                        merged.get(column), other.get(column), other.get("fuente")
                    )
                elif column in {"rating", "reseñas"}:
                    merged[column] = max(merged.get(column) or 0, other.get(column) or 0)
                elif not _meaningful(merged.get(column)) and _meaningful(other.get(column)):
                    merged[column] = other[column]
        update_columns = [column for column in columns if column != "id"]
        conn.execute(
            f"UPDATE leads SET {','.join(f'{column} = ?' for column in update_columns)} WHERE id = ?",
            [merged.get(column) for column in update_columns] + [keep_id],
        )
        conn.executemany("DELETE FROM leads WHERE id = ?", [(value,) for value in ids[1:]])


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
        place_id TEXT,
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
        perfil_url TEXT,
        telefono_e164 TEXT,
        instagram TEXT,
        facebook TEXT,
        linkedin_empresa TEXT,
        pixel_fb BOOLEAN DEFAULT FALSE,
        pixel_google BOOLEAN DEFAULT FALSE,
        decisor TEXT,
        verificado BOOLEAN DEFAULT FALSE)''')

    # Migraciones versionadas (solo se aplican si la versión guardada es menor)
    current = _get_schema_version(conn)
    if current < SCHEMA_VERSION:
        _migrate(conn, current)
        _set_schema_version(conn, SCHEMA_VERSION)

    # Autocorrección: una copia restaurada con la versión adelantada no debe
    # quedarse sin columnas nuevas (la versión guardada no se recalcula hacia atrás).
    existing = {row[1] for row in conn.execute("PRAGMA table_info(leads)").fetchall()}
    for column, type_def in {
        "mision_id": "TEXT",
        "follow_ups_sent": "INTEGER DEFAULT 0",
        "decisor_nombre": "TEXT",
        "decisor_cargo": "TEXT",
        "decisor_linkedin": "TEXT",
        "reunion_at": "TEXT",
        "reunion_url": "TEXT",
    }.items():
        if column not in existing:
            logger.warning(f"Base de datos: columna {column} ausente; añadiéndola.")
            conn.execute(f"ALTER TABLE leads ADD COLUMN {column} {type_def}")

    # Índices (idempotentes y baratos)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ciudad ON leads(ciudad)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nicho ON leads(nicho)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nit ON leads(nit)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_calificacion ON leads(calificacion)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_estado ON leads(estado)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_place_id ON leads(place_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_phone_e164 ON leads(telefono_e164)")
    # Identidad: place_id estable o (nombre, ciudad) si no hay place_id.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_place_id "
        "ON leads(place_id) WHERE place_id IS NOT NULL"
    )
    conn.execute("DROP INDEX IF EXISTS idx_unique_nombre_ciudad_no_pid")
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_identity_no_pid ON leads("
            "lower(trim(nombre)), lower(trim(COALESCE(ciudad, ''))), "
            "lower(trim(COALESCE(pais, '')))) WHERE place_id IS NULL"
        )
    except sqlite3.IntegrityError:
        # Bases restauradas o importadas pueden traer identidades duplicadas;
        # consolidarlas primero evita que la app no arranque.
        logger.warning(
            "Identidades duplicadas detectadas; consolidando antes de crear el índice único."
        )
        _consolidate_normalized_identity_duplicates(conn)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_identity_no_pid ON leads("
            "lower(trim(nombre)), lower(trim(COALESCE(ciudad, ''))), "
            "lower(trim(COALESCE(pais, '')))) WHERE place_id IS NULL"
        )

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
    history_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(search_history)").fetchall()
    }
    for column in ("product_campaign", "target_segments", "mision_id", "nombre"):
        if column not in history_columns:
            conn.execute(f"ALTER TABLE search_history ADD COLUMN {column} TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_fecha ON search_history(fecha)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_mision ON search_history(mision_id)")

    conn.execute('''CREATE TABLE IF NOT EXISTS search_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE,
        nicho TEXT,
        pais TEXT,
        ciudades TEXT,
        fuentes TEXT,
        limit_sel INTEGER,
        deep_scan BOOLEAN,
        product_campaign TEXT,
        target_segments TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    favorite_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(search_favorites)").fetchall()
    }
    for column in ("product_campaign", "target_segments", "cold_call_mode", "hunter_mode", "carpeta"):
        if column not in favorite_columns:
            conn.execute(f"ALTER TABLE search_favorites ADD COLUMN {column} TEXT")

    conn.execute('''CREATE TABLE IF NOT EXISTS lead_opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL,
        product_key TEXT NOT NULL,
        product_label TEXT NOT NULL,
        segment_key TEXT NOT NULL DEFAULT '',
        segment_label TEXT,
        fit_score INTEGER DEFAULT 0,
        fit_reason TEXT,
        pitch TEXT,
        decision_roles TEXT,
        source_query TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(lead_id, product_key, segment_key),
        FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE
    )''')
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_opportunity_product "
        "ON lead_opportunities(product_key, fit_score DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_opportunity_lead "
        "ON lead_opportunities(lead_id)"
    )

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

    conn.execute('''CREATE TABLE IF NOT EXISTS campaign_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        lead_id INTEGER,
        destination TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        error TEXT,
        provider_message_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(campaign_id, channel, destination),
        FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE SET NULL
    )''')
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_campaign_status "
        "ON campaign_events(campaign_id, status)"
    )

    conn.execute('''CREATE TABLE IF NOT EXISTS webhook_events (
        event_id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'processing',
        attempts INTEGER NOT NULL DEFAULT 1,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        error TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS email_sends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destino TEXT NOT NULL,
        provider TEXT,
        status TEXT NOT NULL DEFAULT 'sent',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_sends_destino ON email_sends(lower(destino))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_sends_fecha ON email_sends(created_at)"
    )

    conn.execute('''CREATE TABLE IF NOT EXISTS segment_status (
        product_key TEXT NOT NULL,
        segment_key TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        reason TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (product_key, segment_key)
    )''')

    # Limpieza proactiva de teléfonos mal formateados o con caracteres extraños en la base de datos
    try:
        rows = conn.execute("SELECT id, telefono FROM leads WHERE telefono IS NOT NULL AND telefono != 'N/A' AND telefono != ''").fetchall()
        updates = []
        for lid, tel in rows:
            cleaned = clean_phone_number(tel)
            if cleaned != tel:
                updates.append((cleaned, lid))
        if updates:
            conn.executemany("UPDATE leads SET telefono = ? WHERE id = ?", updates)
            logger.info(f"Base de datos: Se normalizaron {len(updates)} números de teléfono antiguos.")
    except Exception as e:
        logger.error(f"Error al normalizar teléfonos antiguos en base de datos: {e}")

    # Limpieza proactiva de sitios web corporativos para marcas famosas sin web
    try:
        rows = conn.execute("SELECT id, nombre, sitio_web FROM leads WHERE sitio_web IS NULL OR sitio_web = '' OR sitio_web = 'N/A' OR sitio_web = 'sin sitio web'").fetchall()
        web_updates = []
        for lid, nombre, web in rows:
            corp_web = resolve_corporate_website(nombre)
            if corp_web:
                web_updates.append((corp_web, 1, lid))
        if web_updates:
            conn.executemany("UPDATE leads SET sitio_web = ?, tiene_web = ? WHERE id = ?", web_updates)
            logger.info(f"Base de datos: Se asignó sitio web corporativo a {len(web_updates)} negocios de marca.")
    except Exception as e:
        logger.error(f"Error al normalizar sitios web corporativos antiguos en base de datos: {e}")

    conn.commit()
    conn.close()



def _extract_place_id_from_url(url: str) -> str | None:
    import re
    m = re.search(r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)", url or "")
    return m.group(1) if m else None


_EMPTY_VALUES = {"", "n/a", "nan", "none", "null", "sin sitio web"}


def _meaningful(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().casefold() not in _EMPTY_VALUES
    return True


def _coerce_float(value) -> float:
    """Convierte valores numéricos locales ('4,5', '4.5/5', 4.5) a float sin lanzar.

    Retorna 0.0 si no se puede parsear. Nunca lanza ValueError.
    """
    import math
    if value is None or value == "":
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return 0.0
        return float(value)
    match = re.search(r"(\d+(?:[.,]\d+)?)", str(value))
    if not match:
        return 0.0
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return 0.0


def _coerce_reviews(value) -> int:
    """Convierte conteos locales ('1,200', '1.200', '2,5 mil', 120.0) a int sin lanzar.

    Retorna 0 si no se puede parsear. Nunca lanza ValueError.
    """
    import math
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return 0
        return int(value)
    s = str(value).strip()
    abbreviated = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|m|mil|mill[oó]n(?:es)?)\b", s, re.IGNORECASE)
    if abbreviated:
        try:
            number = float(abbreviated.group(1).replace(",", "."))
        except ValueError:
            number = 0.0
        suffix = abbreviated.group(2).casefold()
        multiplier = 1_000 if suffix in {"k", "mil"} else 1_000_000
        return int(round(number * multiplier))
    digits = "".join(ch for ch in s if ch.isdigit())
    return int(digits) if digits else 0


def _json_list(value) -> list:
    if isinstance(value, list):
        return [str(item) for item in value if _meaningful(item)]
    if not _meaningful(value):
        return []
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else [str(loaded)]
    except (TypeError, ValueError, json.JSONDecodeError):
        return [str(value)]


def _json_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if not _meaningful(value):
        return {}
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {"legacy": loaded}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"legacy": str(value)}


def _merge_raw_data(existing, incoming, source: str | None) -> str:
    current = dict(_json_dict(existing))
    new_data = dict(_json_dict(incoming))
    for key, value in new_data.items():
        if _meaningful(value) and not _meaningful(current.get(key)):
            current[key] = value
    if source and new_data:
        by_source = current.get("_by_source")
        if not isinstance(by_source, dict):
            by_source = {}
        by_source[source] = new_data
        current["_by_source"] = by_source
    return json.dumps(current, ensure_ascii=False, default=str)


def _save_lead_opportunity(conn, lead_id: int, lead) -> None:
    """Guarda la afinidad producto↔lead sin duplicar la ficha del negocio."""
    product_key = str(getattr(lead, "campaign_key", "") or "").strip()
    product_label = str(getattr(lead, "campaign_label", "") or "").strip()
    if not product_key or not product_label or product_key == "busqueda_libre":
        return

    segment_key = str(getattr(lead, "target_segment_key", "") or "").strip()
    conn.execute(
        """
        INSERT INTO lead_opportunities
            (lead_id, product_key, product_label, segment_key, segment_label,
             fit_score, fit_reason, pitch, decision_roles, source_query)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(lead_id, product_key, segment_key) DO UPDATE SET
            product_label=excluded.product_label,
            segment_label=excluded.segment_label,
            fit_score=MAX(lead_opportunities.fit_score, excluded.fit_score),
            fit_reason=excluded.fit_reason,
            pitch=excluded.pitch,
            decision_roles=excluded.decision_roles,
            source_query=excluded.source_query,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            lead_id,
            product_key,
            product_label,
            segment_key,
            getattr(lead, "target_segment", None),
            int(getattr(lead, "fit_score", 0) or 0),
            getattr(lead, "fit_reason", None),
            getattr(lead, "pitch_sugerido", None),
            getattr(lead, "decision_roles", None),
            getattr(lead, "source_query", None),
        ),
    )


def _find_existing_id(conn, lead, place_id: str | None) -> int | None:
    if place_id:
        row = conn.execute(
            "SELECT id FROM leads WHERE place_id = ? LIMIT 1", (place_id,)
        ).fetchone()
        if row:
            return row[0]

    nit = str(getattr(lead, "nit", "") or "").strip()
    if _meaningful(nit):
        rows = conn.execute(
            "SELECT id, place_id FROM leads WHERE nit = ? ORDER BY id", (nit,)
        ).fetchall()
        if place_id:
            # Un NIT puede pertenecer a varias sedes. Solo promocionamos un row
            # todavía sin identidad de Maps; nunca fusionamos dos place_id distintos.
            without_place_id = [row for row in rows if not row[1]]
            if len(without_place_id) == 1:
                return without_place_id[0][0]
        elif len(rows) == 1:
            return rows[0][0]

    name = str(getattr(lead, "nombre", "") or "").strip()
    city = str(getattr(lead, "ciudad", "") or "").strip()
    country = str(getattr(lead, "pais", "") or "").strip()
    if not name:
        return None
    rows = conn.execute(
        """
        SELECT id, place_id, pais FROM leads
        WHERE lower(trim(nombre)) = lower(trim(?))
          AND lower(trim(COALESCE(ciudad, ''))) = lower(trim(?))
          AND (
              lower(trim(COALESCE(pais, ''))) = lower(trim(?))
              OR COALESCE(trim(pais), '') = ''
          )
        ORDER BY CASE WHEN place_id IS NULL THEN 0 ELSE 1 END, id
        """,
        (name, city, country),
    ).fetchall()
    if place_id:
        no_pid = [row for row in rows if not row[1]]
        if len(no_pid) == 1:
            return no_pid[0][0]
        return None
    if len(rows) == 1:
        return rows[0][0]
    return None


def save_lead(lead, conn, mision_id=None):
    """Inserta o enriquece un lead (objeto `Lead`).

    `mision_id` identifica la búsqueda que capturó el lead (atribución exacta).
    En un merge (duplicado) NO se sobreescribe: el lead conserva su primera misión.

    Retorna:
      1 si es un lead NUEVO insertado.
      0 si es un lead EXISTENTE actualizado/fusionado.
     -1 si hubo un error.
    """
    if not hasattr(lead, "nombre"):
        logger.error(f"save_lead: se esperaba un objeto Lead, recibido {type(lead).__name__}")
        return -1

    # Normalizar con el pais del propio lead, nunca con el pais actual de la UI.
    if hasattr(lead, "telefono") and lead.telefono:
        lead.telefono = clean_phone_number(str(lead.telefono))
    lead.telefono_e164 = normalize_phone(
        getattr(lead, "telefono", None), getattr(lead, "pais", None)
    )

    # Validar sitio web corporativo de marcas famosas
    if hasattr(lead, "sitio_web"):
        site = (lead.sitio_web or "").strip()
        if not site or site.upper() == "N/A" or site.lower() == "sin sitio web":
            corp_web = resolve_corporate_website(lead.nombre)
            if corp_web:
                lead.sitio_web = corp_web
                lead.tiene_web = True

    place_id = getattr(lead, "place_id", None) or _extract_place_id_from_url(
        getattr(lead, "maps_url", None)
    )
    existing_id = _find_existing_id(conn, lead, place_id)

    if existing_id is not None:
        if _merge_into_existing(conn, existing_id, lead, place_id):
            _save_lead_opportunity(conn, existing_id, lead)
            return 0  # Actualizado
        return -1

    fuentes = list(dict.fromkeys(
        _json_list(getattr(lead, "fuentes_encontrado", []))
        + _json_list(getattr(lead, "fuente", None))
    ))
    fuentes_json = json.dumps(fuentes, ensure_ascii=False)
    raw_json = _merge_raw_data({}, getattr(lead, "raw_data", {}), getattr(lead, "fuente", None))
    site = getattr(lead, "sitio_web", None)
    has_site = bool(_meaningful(site))

    # No existe → INSERT
    try:
        cursor = conn.execute(
            """
            INSERT INTO leads
               (nombre, ciudad, departamento, pais, zona, direccion, telefono, telefono_e164,
                email, sitio_web, perfil_url, tiene_web,
                rating, reseñas, maps_url, place_id, nicho, sector, tipo, fuente, fuentes_encontrado, nit,
                calificacion, lat, lng, instagram, facebook, linkedin_empresa,
                pixel_fb, pixel_google, decisor, verificado, raw_data, mision_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead.nombre, lead.ciudad, getattr(lead, "departamento", None),
                getattr(lead, "pais", None), getattr(lead, "zona", None), lead.direccion,
                lead.telefono, lead.telefono_e164, lead.email, site,
                getattr(lead, "perfil_url", None), has_site, lead.rating,
                getattr(lead, 'reseñas', 0), getattr(lead, 'maps_url', None), place_id,
                lead.nicho, lead.sector, lead.tipo, lead.fuente, fuentes_json,
                lead.nit, lead.calificacion, lead.lat, lead.lng,
                lead.instagram, lead.facebook, lead.linkedin_empresa,
                lead.pixel_fb, lead.pixel_google, lead.decisor, lead.verificado, raw_json,
                mision_id,
            ),
        )
        _save_lead_opportunity(conn, cursor.lastrowid, lead)
        return 1  # Nuevo
    except sqlite3.IntegrityError:
        # Race de concurrencia: otro hilo insertó la misma identidad justo después
        # de nuestro chequeo. Re-buscamos el row ganador y fusionamos en vez de
        # descartar los datos del lead.
        logger.warning(
            f"save_lead INSERT integrity: identidad duplicada por concurrencia "
            f"({getattr(lead, 'nombre', '')[:40]}); intentando fusionar."
        )
        try:
            existing_id = _find_existing_id(conn, lead, place_id)
            if existing_id is not None and _merge_into_existing(conn, existing_id, lead, place_id):
                _save_lead_opportunity(conn, existing_id, lead)
                return 0  # Actualizado
        except Exception as merge_error:
            logger.error(f"save_lead merge tras IntegrityError: {merge_error}")
        return -1
    except Exception as e:
        logger.error(f"save_lead INSERT: {e}")
        return -1


def _merge_into_existing(conn, existing_id, lead, place_id):
    """Fusiona el lead contra un row ya existente.

    Promociona `place_id` y `maps_url` si el row existente no los tenía.
    El resto de campos se rellenan solo si el destino está vacío (NULLIF).
    """
    try:
        conn.row_factory = sqlite3.Row
        current = conn.execute("SELECT * FROM leads WHERE id = ?", (existing_id,)).fetchone()
        if not current:
            return False
        current = dict(current)

        incoming_phone = normalize_phone(
            getattr(lead, "telefono", None), getattr(lead, "pais", None)
        )
        sources = list(dict.fromkeys(
            _json_list(current.get("fuentes_encontrado"))
            + _json_list(getattr(lead, "fuentes_encontrado", []))
            + _json_list(getattr(lead, "fuente", None))
        ))
        score_rank = {"frio": 0, "bueno": 1, "oro": 2}
        old_score = str(current.get("calificacion") or "frio").casefold()
        new_score = str(getattr(lead, "calificacion", "frio") or "frio").casefold()
        best_score = new_score if score_rank.get(new_score, 0) > score_rank.get(old_score, 0) else old_score

        def pick(column, value):
            return value if _meaningful(value) and not _meaningful(current.get(column)) else current.get(column)

        site = pick("sitio_web", getattr(lead, "sitio_web", None))
        values = {
            "telefono": pick("telefono", getattr(lead, "telefono", None)) if incoming_phone else current.get("telefono"),
            "telefono_e164": pick("telefono_e164", incoming_phone),
            "email": pick("email", getattr(lead, "email", None)),
            "sitio_web": site,
            "perfil_url": pick("perfil_url", getattr(lead, "perfil_url", None)),
            "tiene_web": int(bool(_meaningful(site))),
            "direccion": pick("direccion", getattr(lead, "direccion", None)),
            "nit": pick("nit", getattr(lead, "nit", None)),
            "rating": max(_coerce_float(current.get("rating")), _coerce_float(getattr(lead, "rating", 0))) or None,
            "reseñas": max(_coerce_reviews(current.get("reseñas")), _coerce_reviews(getattr(lead, "reseñas", 0))),
            "maps_url": pick("maps_url", getattr(lead, "maps_url", None)),
            "place_id": pick("place_id", place_id),
            "pais": pick("pais", getattr(lead, "pais", None)),
            "departamento": pick("departamento", getattr(lead, "departamento", None)),
            "zona": pick("zona", getattr(lead, "zona", None)),
            "lat": pick("lat", getattr(lead, "lat", None)),
            "lng": pick("lng", getattr(lead, "lng", None)),
            "nicho": pick("nicho", getattr(lead, "nicho", None)),
            "sector": pick("sector", getattr(lead, "sector", None)),
            "tipo": pick("tipo", getattr(lead, "tipo", None)),
            "instagram": pick("instagram", getattr(lead, "instagram", None)),
            "facebook": pick("facebook", getattr(lead, "facebook", None)),
            "linkedin_empresa": pick("linkedin_empresa", getattr(lead, "linkedin_empresa", None)),
            "pixel_fb": int(bool(current.get("pixel_fb") or getattr(lead, "pixel_fb", False))),
            "pixel_google": int(bool(current.get("pixel_google") or getattr(lead, "pixel_google", False))),
            "decisor": pick("decisor", getattr(lead, "decisor", None)),
            "verificado": int(bool(current.get("verificado") or getattr(lead, "verificado", False))),
            "calificacion": best_score,
            "fuentes_encontrado": json.dumps(sources, ensure_ascii=False),
            "raw_data": _merge_raw_data(
                current.get("raw_data"), getattr(lead, "raw_data", {}), getattr(lead, "fuente", None)
            ),
        }
        assignments = ", ".join(f"{column} = ?" for column in values)
        conn.execute(
            f"UPDATE leads SET {assignments} WHERE id = ?",
            [*values.values(), existing_id],
        )
        return True
    except Exception as e:
        logger.error(f"_merge_into_existing: {e}")
        return False



def update_lead_field(lead_id, campo, valor):
    """Actualiza un campo específico de un lead por su ID."""
    allowed_fields = {
        "estado",
        "calificacion",
        "notas",
        "ultima_interaccion",
        "estado_contacto",
        "bot_pausado",
        "whatsapp_id",
        "fecha_ultimo_contacto",
    }
    if campo not in allowed_fields:
        logger.warning(f"Campo no permitido para actualizar: {campo}")
        return False

    conn = None
    try:
        conn = open_conn()
        conn.execute(f"UPDATE leads SET {campo} = ? WHERE id = ?", (valor, lead_id))
        conn.commit()
        # Streamlit conserva el DataFrame hasta 30 s. Limpiarlo aquí evita que
        # el CRM compare contra el valor antiguo y entre en reruns repetidos.
        from services.leads import invalidate_leads_cache
        invalidate_leads_cache()
        return True
    except Exception as e:
        logger.error(f"Error actualizando lead {lead_id}: {e}")
        return False
    finally:
        if conn is not None:
            conn.close()


_PORTFOLIO_DELETE_RULES = {
    "divi": {"key_prefix": "divi_", "label_prefix": "divi%"},
    "watson": {"key_prefix": "watson_", "label_prefix": "watson%"},
    "onyx": {"key_prefix": "onyx_", "label_prefix": "onyx%"},
}


def delete_portfolio_batch(lead_ids, portfolio_key: str) -> dict:
    """Borra un lote sin eliminar fichas que aún pertenecen a otro portafolio.

    Para DIVI/Watson/ONYX primero elimina las oportunidades del portafolio. La
    ficha completa solo se borra si ya no conserva ninguna otra oportunidad.
    ``unassigned`` elimina únicamente IDs que siguen sin un portafolio conocido.
    """
    if portfolio_key not in {*_PORTFOLIO_DELETE_RULES, "unassigned"}:
        raise ValueError("Lote no permitido para eliminación.")

    normalized = set()
    for raw_lead_id in lead_ids:
        try:
            lead_id = int(raw_lead_id)
        except (TypeError, ValueError):
            continue
        if lead_id > 0:
            normalized.add(lead_id)
    normalized_ids = sorted(normalized)
    result = {
        "requested": len(normalized_ids),
        "matched": 0,
        "leads_deleted": 0,
        "leads_preserved": 0,
        "associations_deleted": 0,
    }
    if not normalized_ids:
        return result

    conn = open_conn()
    try:
        with conn:
            conn.execute("DROP TABLE IF EXISTS temp.selected_batch_ids")
            conn.execute(
                "CREATE TEMP TABLE selected_batch_ids "
                "(id INTEGER PRIMARY KEY) WITHOUT ROWID"
            )
            conn.executemany(
                "INSERT INTO selected_batch_ids(id) VALUES (?)",
                [(lead_id,) for lead_id in normalized_ids],
            )

            if portfolio_key == "unassigned":
                known_clauses = []
                known_params = []
                for rule in _PORTFOLIO_DELETE_RULES.values():
                    known_clauses.append(
                        "(o.product_key LIKE ? OR lower(o.product_label) LIKE ?)"
                    )
                    known_params.extend([
                        f"{rule['key_prefix']}%", rule["label_prefix"]
                    ])
                known_sql = " OR ".join(known_clauses)
                matched_ids = [
                    row[0]
                    for row in conn.execute(
                        f"""
                        SELECT l.id
                        FROM leads l
                        JOIN selected_batch_ids s ON s.id = l.id
                        WHERE NOT EXISTS (
                            SELECT 1 FROM lead_opportunities o
                            WHERE o.lead_id = l.id AND ({known_sql})
                        )
                        """,
                        known_params,
                    ).fetchall()
                ]
            else:
                rule = _PORTFOLIO_DELETE_RULES[portfolio_key]
                match_sql = (
                    "(o.product_key LIKE ? OR lower(o.product_label) LIKE ?)"
                )
                match_params = [
                    f"{rule['key_prefix']}%", rule["label_prefix"]
                ]
                matched_ids = [
                    row[0]
                    for row in conn.execute(
                        f"""
                        SELECT DISTINCT o.lead_id
                        FROM lead_opportunities o
                        JOIN selected_batch_ids s ON s.id = o.lead_id
                        WHERE {match_sql}
                        """,
                        match_params,
                    ).fetchall()
                ]

            result["matched"] = len(matched_ids)
            if not matched_ids:
                return result

            conn.execute("DROP TABLE IF EXISTS temp.matched_batch_ids")
            conn.execute(
                "CREATE TEMP TABLE matched_batch_ids "
                "(id INTEGER PRIMARY KEY) WITHOUT ROWID"
            )
            conn.executemany(
                "INSERT INTO matched_batch_ids(id) VALUES (?)",
                [(lead_id,) for lead_id in matched_ids],
            )

            if portfolio_key == "unassigned":
                result["associations_deleted"] = conn.execute(
                    """
                    SELECT COUNT(*) FROM lead_opportunities
                    WHERE lead_id IN (SELECT id FROM matched_batch_ids)
                    """
                ).fetchone()[0]
                conn.execute(
                    "DELETE FROM leads "
                    "WHERE id IN (SELECT id FROM matched_batch_ids)"
                )
                result["leads_deleted"] = len(matched_ids)
            else:
                rule = _PORTFOLIO_DELETE_RULES[portfolio_key]
                match_sql = (
                    "(product_key LIKE ? OR lower(product_label) LIKE ?)"
                )
                match_params = [
                    f"{rule['key_prefix']}%", rule["label_prefix"]
                ]
                result["associations_deleted"] = conn.execute(
                    f"""
                    SELECT COUNT(*) FROM lead_opportunities
                    WHERE lead_id IN (SELECT id FROM matched_batch_ids)
                      AND {match_sql}
                    """,
                    match_params,
                ).fetchone()[0]
                conn.execute(
                    f"""
                    DELETE FROM lead_opportunities
                    WHERE lead_id IN (SELECT id FROM matched_batch_ids)
                      AND {match_sql}
                    """,
                    match_params,
                )
                deletable_ids = [
                    row[0]
                    for row in conn.execute(
                        """
                        SELECT m.id FROM matched_batch_ids m
                        WHERE NOT EXISTS (
                            SELECT 1 FROM lead_opportunities o
                            WHERE o.lead_id = m.id
                        )
                        """
                    ).fetchall()
                ]
                if deletable_ids:
                    conn.executemany(
                        "DELETE FROM leads WHERE id = ?",
                        [(lead_id,) for lead_id in deletable_ids],
                    )
                result["leads_deleted"] = len(deletable_ids)
                result["leads_preserved"] = len(matched_ids) - len(deletable_ids)
    except Exception:
        logger.exception("Error borrando el lote de portafolio {}", portfolio_key)
        raise
    finally:
        conn.close()

    if result["matched"]:
        from services.leads import invalidate_leads_cache
        invalidate_leads_cache()
    return result


def load_known_identifiers(ciudad: str, conn) -> tuple[set, set]:
    """Carga identificadores conocidos (nombres y Place IDs) usando la columna indexada."""
    nombres = {
        r[0].lower()
        for r in conn.execute("SELECT nombre FROM leads WHERE ciudad = ?", (ciudad,)).fetchall()
        if r[0]
    }
    cids = {
        r[0]
        for r in conn.execute("SELECT place_id FROM leads WHERE place_id IS NOT NULL").fetchall()
        if r[0]
    }
    return nombres, cids


def save_search_history(
    ciudad, pais, nicho, zona, leads_nuevos, leads_duplicados, conn,
    product_campaign=None, target_segments=None, mision_id=None,
):
    """Historial de búsqueda."""
    conn.execute(
        """
        INSERT INTO search_history
            (fecha, ciudad, pais, nicho, zona, leads_nuevos, leads_duplicados,
             product_campaign, target_segments, mision_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            ciudad, pais, nicho, zona, leads_nuevos, leads_duplicados,
            product_campaign, json.dumps(target_segments or [], ensure_ascii=False),
            mision_id,
        )
    )
    conn.commit()


def claim_campaign_destination(campaign_id, channel, lead_id, destination) -> bool:
    """Reserva un destino de forma atomica para impedir reenvios al reanudar."""
    with open_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO campaign_events
                (campaign_id, channel, lead_id, destination, status)
            VALUES (?, ?, ?, ?, 'processing')
            ON CONFLICT(campaign_id, channel, destination) DO NOTHING
            """,
            (campaign_id, channel, lead_id, destination),
        )
        return cursor.rowcount == 1


def finish_campaign_destination(
    campaign_id, channel, destination, status, error=None, provider_message_id=None
):
    """Cierra el evento persistente de una campana."""
    with open_conn() as conn:
        conn.execute(
            """
            UPDATE campaign_events
            SET status = ?, error = ?, provider_message_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE campaign_id = ? AND channel = ? AND destination = ?
            """,
            (status, error, provider_message_id, campaign_id, channel, destination),
        )


def claim_webhook_event(event_id: str) -> bool:
    """Idempotencia: Evolution puede reenviar el mismo evento varias veces."""
    if not event_id:
        return True
    with open_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO webhook_events(event_id, status)
            VALUES (?, 'processing')
            ON CONFLICT(event_id) DO UPDATE SET
                status = 'processing', attempts = webhook_events.attempts + 1,
                updated_at = CURRENT_TIMESTAMP, error = NULL
            WHERE webhook_events.status = 'error' AND webhook_events.attempts < 3
            """,
            (event_id,),
        )
        return cursor.rowcount == 1


def finish_webhook_event(event_id: str, status: str, error: str | None = None):
    if not event_id:
        return
    with open_conn() as conn:
        conn.execute(
            """
            UPDATE webhook_events
            SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP
            WHERE event_id = ?
            """,
            (status, error, event_id),
        )

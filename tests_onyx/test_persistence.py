import sys
import os
import sqlite3
import json
import tempfile
import pytest

# Añadir el directorio raíz al path para importar db y fuentes
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import save_lead, init_db, open_conn
import db
from sources.base_source import Lead

# DB de pruebas aislada (fuera del directorio de producción data/)
TEST_DB = os.path.join(tempfile.gettempdir(), "onyx_test_leads.db")

def _cleanup():
    for path in (TEST_DB, f"{TEST_DB}-wal", f"{TEST_DB}-shm"):
        if os.path.exists(path):
            os.remove(path)

def setup_module():
    _cleanup()
    db.DB_PATH = TEST_DB
    init_db()

def teardown_module():
    _cleanup()

def test_upsert_enrichment():
    conn = open_conn()
    
    # Lead inicial
    lead1 = Lead(
        nombre="Empresa Test",
        ciudad="Medellin",
        nicho="Software",
        fuente="google_maps",
        direccion="Calle 123",
        telefono="1234567"
    )
    
    # Guardar primer lead
    success1 = save_lead(lead1, conn)
    assert success1 == 1
    
    # Verificar inserción
    cursor = conn.execute("SELECT telefono, email, nit, fuentes_encontrado FROM leads WHERE nombre='Empresa Test'")
    row = cursor.fetchone()
    assert row[0] == "1234567"
    assert row[1] is None
    assert "google_maps" in json.loads(row[3])
    
    # Lead con información adicional (mismo nombre y ciudad)
    lead2 = Lead(
        nombre="Empresa Test",
        ciudad="Medellin",
        nicho="Software",
        fuente="rues",
        email="test@empresa.com",
        nit="900123456-1",
        sitio_web="https://empresa.com"
    )
    
    # Guardar segundo lead (UPSERT)
    success2 = save_lead(lead2, conn)
    assert success2 == 0
    
    # Verificar enriquecimiento
    cursor = conn.execute("SELECT telefono, email, nit, sitio_web, fuentes_encontrado FROM leads WHERE nombre='Empresa Test'")
    row = cursor.fetchone()
    assert row[0] == "1234567" # Mantiene el anterior
    assert row[1] == "test@empresa.com" # Se añade el nuevo
    assert row[2] == "900123456-1" # Se añade el nuevo
    assert row[3] == "https://empresa.com" # Se añade el nuevo
    
    fuentes = row[4]
    assert "google_maps" in fuentes
    assert "rues" in fuentes
    
    conn.close()

if __name__ == "__main__":
    setup_module()
    try:
        test_upsert_enrichment()
        print("✅ Unit Test (Persistencia) PASSED")
    except Exception as e:
        print(f"❌ Unit Test (Persistencia) FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        teardown_module()

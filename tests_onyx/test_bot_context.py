import sys
import os
import tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db

# Mock DB
TEST_DB = os.path.join(tempfile.gettempdir(), "onyx_test_bot.db")
db.DB_PATH = TEST_DB
import webhook

def test_bot_context_retrieval():
    for path in (TEST_DB, f"{TEST_DB}-wal", f"{TEST_DB}-shm"):
        if os.path.exists(path):
            os.remove(path)
    db.init_db()
    
    conn = db.open_conn()
    # Insertar un lead con un whatsapp_id específico
    conn.execute(
        "INSERT INTO leads (nombre, ciudad, telefono, whatsapp_id, sector, calificacion) VALUES (?, ?, ?, ?, ?, ?)",
        ("Cliente Bot", "Bogota", "3001234567", "573001234567@s.whatsapp.net", "educacion", "oro")
    )
    conn.commit()
    conn.close()
    
    # Simular recuperación de contexto
    context = webhook.get_lead_context("573001234567@s.whatsapp.net")
    
    assert context is not None
    assert context['nombre'] == "Cliente Bot"
    assert context['sector'] == "educacion"
    assert context['calificacion'] == "oro"
    
    # Probar con número de teléfono (match parcial)
    context2 = webhook.get_lead_context("573001234567@c.us")
    assert context2 is not None
    assert context2['nombre'] == "Cliente Bot"

    for path in (TEST_DB, f"{TEST_DB}-wal", f"{TEST_DB}-shm"):
        if os.path.exists(path):
            os.remove(path)
    print("✅ Validation (Bot Context) PASSED")

if __name__ == "__main__":
    try:
        test_bot_context_retrieval()
    except Exception as e:
        print(f"❌ Validation (Bot Context) FAILED: {e}")
        import traceback
        traceback.print_exc()

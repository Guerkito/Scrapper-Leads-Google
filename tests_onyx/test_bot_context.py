import sys
import os
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db

# Mock DB
TEST_DB = "data/test_bot.db"
db.DB_PATH = TEST_DB
import webhook
webhook.DB_PATH = TEST_DB

def test_bot_context_retrieval():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
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

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    print("✅ Validation (Bot Context) PASSED")

if __name__ == "__main__":
    try:
        test_bot_context_retrieval()
    except Exception as e:
        print(f"❌ Validation (Bot Context) FAILED: {e}")
        import traceback
        traceback.print_exc()

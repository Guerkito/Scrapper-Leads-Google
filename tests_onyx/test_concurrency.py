import sys
import os
import asyncio
import random
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db
from sources.base_source import Lead

TEST_DB = "data/test_stress.db"
db.DB_PATH = TEST_DB

async def concurrent_save(id_task, conn):
    lead = Lead(
        nombre=f"Empresa Concurrente {id_task % 5}", # Solo 5 empresas diferentes para forzar colisiones
        ciudad="Bogota",
        nicho="Stress",
        fuente=f"fuente_{id_task}",
        telefono=str(random.randint(1000000, 9999999))
    )
    # En un entorno real, cada tarea podría intentar abrir su propia conexión o usar una compartida
    # SQLite WAL maneja múltiples lectores y un escritor.
    success = db.save_lead(lead, conn)
    return success

async def test_concurrency():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db.init_db()
    
    conn = db.open_conn()
    
    print("🚀 Iniciando 100 inserciones concurrentes...")
    tasks = [concurrent_save(i, conn) for i in range(100)]
    results = await asyncio.gather(*tasks)
    
    conn.commit()
    conn.close()
    
    success_count = sum(1 for r in results if r)
    print(f"✅ Éxitos: {success_count}/100")
    
    assert success_count == 100
    
    # Verificar que solo hay 5 registros únicos por nombre/ciudad
    conn = db.open_conn()
    count = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    conn.close()
    
    print(f"📊 Registros finales en DB: {count}")
    assert count == 5
    
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    print("✅ Stress Test (Concurrencia) PASSED")

if __name__ == "__main__":
    asyncio.run(test_concurrency())

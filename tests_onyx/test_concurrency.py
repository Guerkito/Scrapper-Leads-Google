import os
import random
from concurrent.futures import ThreadPoolExecutor
import pytest

import db
from sources.base_source import Lead


def test_concurrent_save_no_data_loss(tmp_path):
    """Varias conexiones insertan simultáneamente identidades que colisionan.

    Regresión del bug de carrera: dos hilos pasaban `_find_existing_id` antes de
    que ninguno hiciera INSERT y el segundo lanzaba IntegrityError perdiendo sus
    campos. Ahora el perdedor debe re-buscar y fusionar, sin pérdida de datos.
    """
    db.DB_PATH = str(tmp_path / "stress.db")
    db.init_db()

    def worker(i):
        conn = db.open_conn()
        try:
            lead = Lead(
                nombre=f"Empresa Concurrente {i % 5}",  # 5 identidades que colisionan
                ciudad="Bogotá",
                nicho="Stress",
                fuente=f"fuente_{i}",
                telefono=str(random.randint(1000000, 9999999)),
                email=f"empresa{i % 5}@test.com",
            )
            result = db.save_lead(lead, conn)
            conn.commit()  # cada hilo persiste su transacción (como el orquestador)
            return result
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(worker, range(100)))

    # Ninguna inserción/fusión debe fallar.
    assert all(r >= 0 for r in results), f"guardados con error: {sum(1 for r in results if r < 0)}"

    with db.open_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        emails = {
            row[0] for row in conn.execute("SELECT DISTINCT email FROM leads")
        }
        # Solo las 5 identidades únicas, y sus emails enriquecieron las fichas.
        assert count == 5
        assert emails == {f"empresa{i}@test.com" for i in range(5)}

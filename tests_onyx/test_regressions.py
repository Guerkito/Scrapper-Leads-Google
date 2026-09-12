import asyncio
import json

import db
from engine.query_expander import expandir_query
from services.campaigns import CampState, SENT_CACHE, campaign_worker
from services.email_service import email_campaign_worker
from services.export_utils import safe_spreadsheet_value
from services.phone_utils import normalize_phone
from services.search_mission import SearchMission
from sources.base_source import Lead


def _fresh_db(tmp_path):
    db.DB_PATH = str(tmp_path / "regressions.db")
    db.init_db()
    return db.open_conn()


def test_merge_preserves_sources_raw_geo_and_best_score(tmp_path):
    conn = _fresh_db(tmp_path)
    first = Lead(
        "Acme", "Bogotá", "Abogados", "linkedin", pais="Colombia",
        perfil_url="https://linkedin.com/company/acme", raw_data={"profile": 1},
    )
    second = Lead(
        "Acme", "Bogotá", "Abogados", "google_maps", pais="Colombia",
        sitio_web="https://acme.co", tiene_web=True, rating=4.8, reseñas=30,
        maps_url="https://maps.google.com/!1s0xabc:0xdef", lat=1.2, lng=2.3,
        calificacion="oro", raw_data={"maps": 2},
    )
    assert db.save_lead(first, conn) == 1
    assert db.save_lead(second, conn) == 0
    conn.commit()
    conn.row_factory = db.sqlite3.Row
    row = dict(conn.execute("SELECT * FROM leads").fetchone())
    conn.close()

    assert row["pais"] == "Colombia"
    assert row["tiene_web"] == 1
    assert row["lat"] == 1.2 and row["lng"] == 2.3
    assert row["calificacion"] == "oro"
    assert json.loads(row["fuentes_encontrado"]) == ["linkedin", "google_maps"]
    assert {"profile", "maps"} <= set(json.loads(row["raw_data"]))


def test_same_name_city_different_country_are_distinct(tmp_path):
    conn = _fresh_db(tmp_path)
    assert db.save_lead(Lead("Acme", "Córdoba", "General", "x", pais="España"), conn) == 1
    assert db.save_lead(Lead("Acme", "Córdoba", "General", "x", pais="Argentina"), conn) == 1
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 2
    conn.close()


def test_distinct_place_ids_are_not_merged_by_name_or_nit(tmp_path):
    conn = _fresh_db(tmp_path)
    first = Lead(
        "Acme", "Bogotá", "Legal", "maps", pais="Colombia", nit="900123456",
        maps_url="https://maps.google.com/!1s0x1:0xaaa",
    )
    second = Lead(
        "Acme", "Bogotá", "Legal", "maps", pais="Colombia", nit="900123456",
        maps_url="https://maps.google.com/!1s0x2:0xbbb",
    )

    assert db.save_lead(first, conn) == 1
    assert db.save_lead(second, conn) == 1
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 2
    conn.close()


def test_stop_keeps_mission_busy_until_worker_finishes():
    class StubOrchestrator:
        stopped = False

        def stop(self):
            self.stopped = True

    mission = SearchMission()
    mission.orchestrator = StubOrchestrator()
    mission.running = True

    mission.stop()

    assert mission.orchestrator.stopped is True
    assert mission.running is True


def test_phone_e164_and_formula_export_protection():
    assert normalize_phone("300 123 4567", "Colombia") == "+573001234567"
    assert normalize_phone("+57 (300) 123-4567", "Colombia") == "+573001234567"
    assert safe_spreadsheet_value("=1+1") == "'=1+1"
    assert safe_spreadsheet_value("  @SUM(A1)").startswith("'")


def test_simulation_is_logged_but_does_not_change_lead(tmp_path):
    conn = _fresh_db(tmp_path)
    cursor = conn.execute(
        """
        INSERT INTO leads(nombre, ciudad, pais, telefono, estado)
        VALUES ('Acme', 'Bogotá', 'Colombia', '3001234567', 'Nuevo')
        """
    )
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()

    SENT_CACHE.clear()
    state = CampState()
    state.reset("campaign-test")
    campaign_worker(
        state,
        [{"id": lead_id, "nombre": "Acme", "ciudad": "Bogotá", "nicho": "x",
          "pais": "Colombia", "telefono": "3001234567", "estado_contacto": "sin_contactar"}],
        "Hola {nombre}", "", "", "", "Colombia", True, (0, 0),
    )
    with db.open_conn() as conn:
        assert conn.execute("SELECT estado FROM leads WHERE id=?", (lead_id,)).fetchone()[0] == "Nuevo"
        assert conn.execute(
            "SELECT status FROM campaign_events WHERE campaign_id='campaign-test'"
        ).fetchone()[0] == "simulated"


def test_email_subject_is_personalized(monkeypatch, tmp_path):
    conn = _fresh_db(tmp_path)
    cursor = conn.execute(
        "INSERT INTO leads(nombre, ciudad, email, estado) VALUES ('Acme', 'Bogotá', 'a@example.com', 'Nuevo')"
    )
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    captured = {}

    def fake_send(to_email, subject, body, html=True):
        captured["subject"] = subject
        return True, "ok"

    monkeypatch.setattr("services.email_service.send_email", fake_send)
    state = CampState()
    state.reset("email-test")
    email_campaign_worker(
        state,
        [{"id": lead_id, "nombre": "Acme", "ciudad": "Bogotá", "nicho": "Legal",
          "rating": 4.5, "email": "a@example.com", "estado_contacto": "sin_contactar"}],
        "Propuesta para {nombre}", "Hola {nombre}", False,
    )
    assert captured["subject"] == "Propuesta para Acme"


def test_visible_niche_expands_locally():
    expanded = asyncio.run(expandir_query("Odontólogos"))
    assert len(expanded) > 1, "El catálogo local debe expandir nichos visibles sin Ollama"
    assert "dentista" in expanded or "Dentistas" in expanded


def test_init_db_self_heals_columns_on_advanced_version(tmp_path):
    db.DB_PATH = str(tmp_path / "selfheal.db")
    db.init_db()
    with db.open_conn() as conn:
        conn.execute("ALTER TABLE leads DROP COLUMN follow_ups_sent")
        conn.execute("UPDATE schema_version SET version = 999")

    db.init_db()

    with db.open_conn() as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(leads)")]
    assert "follow_ups_sent" in columns

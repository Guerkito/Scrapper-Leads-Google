import db
from engine import decision_maker as dm


def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "decisions.db"))
    db.init_db()


def test_parse_decision_only_accepts_linkedin_seen_on_site():
    content = (
        '{"nombre": "Ana Pérez", "cargo": "Gerente", '
        '"linkedin": "https://linkedin.com/in/ana-perez"}'
    )

    rejected = dm.parse_decision(content, ["https://www.linkedin.com/in/otra-persona"])
    assert rejected["nombre"] == "Ana Pérez"
    assert rejected["linkedin"] is None

    accepted = dm.parse_decision(content, ["https://www.linkedin.com/in/ana-perez"])
    assert accepted["linkedin"] == "https://linkedin.com/in/ana-perez"


def test_parse_decision_nulls_everything_without_name():
    result = dm.parse_decision(
        '{"nombre": null, "cargo": "Gerente", "linkedin": "https://linkedin.com/in/x"}'
    )
    assert result == {"nombre": None, "cargo": None, "linkedin": None}


def test_enrich_batch_saves_decision(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    with db.open_conn() as conn:
        conn.execute(
            "INSERT INTO leads (nombre, ciudad, sitio_web) "
            "VALUES ('Acme', 'Bogotá', 'https://acme.co')"
        )

    monkeypatch.setattr(
        dm, "_fetch_site",
        lambda url, timeout=12: ("Acme, gerente Ana Pérez", ["https://linkedin.com/in/ana"]),
    )
    monkeypatch.setattr(
        dm, "_ask_llm",
        lambda texto, links: {
            "nombre": "Ana Pérez", "cargo": "Gerente",
            "linkedin": "https://linkedin.com/in/ana",
        },
    )

    assert dm.enrich_batch(limit=5) == 1

    with db.open_conn() as conn:
        row = conn.execute(
            "SELECT decisor_nombre, decisor_cargo, decisor_linkedin FROM leads WHERE nombre = 'Acme'"
        ).fetchone()
    assert row == ("Ana Pérez", "Gerente", "https://linkedin.com/in/ana")
    assert dm.pending_count() == 0

import db
from services import campaign_analytics as analytics
from services import email_service


def _seed_lead(conn, nombre, estado="Contactado", email=None, historial=None):
    conn.execute(
        "INSERT INTO leads (nombre, ciudad, estado, email, historial_mensajes) "
        "VALUES (?, 'Bogotá', ?, ?, ?)",
        (nombre, estado, email or f"{nombre.casefold()}@example.com", historial),
    )
    lead_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return lead_id


def _opportunity(conn, lead_id, product, segment, label):
    conn.execute(
        "INSERT INTO lead_opportunities "
        "(lead_id, product_key, product_label, segment_key, segment_label) "
        "VALUES (?, ?, ?, ?, ?)",
        (lead_id, product, product.replace("_", " ").title(), segment, label),
    )


def _seed_send(conn, destino):
    conn.execute("INSERT INTO email_sends (destino, provider) VALUES (?, 'smtp')", (destino,))


def test_campaign_performance_matches_leads_and_costs(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "analytics.db"))
    db.init_db()
    with db.open_conn() as conn:
        a = _seed_lead(conn, "Clinica A", email="clinicaa@example.com")
        b = _seed_lead(conn, "Clinica B", estado="Interesado", email="clinicab@example.com")
        _opportunity(conn, a, "web_clinicas", "clinicas", "Clínicas")
        _opportunity(conn, b, "web_clinicas", "clinicas", "Clínicas")
        _seed_send(conn, "clinicaa@example.com")
        _seed_send(conn, "clinicab@example.com")

    rows = analytics.campaign_performance(cost_per_email=0.01)

    assert len(rows) == 1
    row = rows[0]
    assert row["leads"] == 2
    assert row["contactados"] == 2
    assert row["respondieron"] == 1
    assert row["emails"] == 2
    assert round(row["coste_por_lead"], 4) == 0.01
    assert row["estado"] == "activo"


def test_auto_optimize_pauses_zero_reply_segment(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "analytics2.db"))
    db.init_db()
    with db.open_conn() as conn:
        for index in range(3):
            lead_id = _seed_lead(conn, f"SinRespuesta {index}")
            _opportunity(conn, lead_id, "web_otros", "sin_respuesta", "Sin respuesta")
        for index in range(3):
            lead_id = _seed_lead(
                conn, f"Bueno {index}", estado="Interesado" if index < 2 else "Contactado"
            )
            _opportunity(conn, lead_id, "web_responden", "buenos", "Buenos")

    actions = analytics.auto_optimize(min_leads=3, scale_rate=0.1)

    paused = {(a["product_key"], a["segment_key"]) for a in actions if a["action"] == "pausar"}
    scaling = {(a["product_key"], a["segment_key"]) for a in actions if a["action"] == "escalar"}
    assert paused == {("web_otros", "sin_respuesta")}
    assert scaling == {("web_responden", "buenos")}
    assert analytics.paused_segment_keys("web_otros") == {("web_otros", "sin_respuesta")}
    assert analytics.paused_segment_keys("web_responden") == set()

    analytics.set_segment_status("web_otros", "sin_respuesta", "active", "Reanudado")
    assert analytics.paused_segment_keys("web_otros") == set()


def test_send_email_respects_daily_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "analytics3.db"))
    db.init_db()
    monkeypatch.setattr(email_service, "SENDER_DAILY_LIMIT", 1)
    with db.open_conn() as conn:
        _seed_send(conn, "alguien@example.com")

    ok, message = email_service.send_email("otro@example.com", "Asunto", "Cuerpo")

    assert ok is False
    assert "Límite diario" in message
    with db.open_conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM email_sends").fetchone()[0] == 1


def test_resend_provider_records_send(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "analytics4.db"))
    db.init_db()
    monkeypatch.setattr(email_service, "SENDER_PROVIDER", "resend")
    monkeypatch.setattr(email_service, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(email_service, "SENDER_DAILY_LIMIT", 0)
    monkeypatch.setattr(email_service, "_send_resend", lambda *args, **kwargs: (True, "Enviado"))

    ok, message = email_service.send_email("destino@example.com", "Asunto", "Cuerpo")

    assert ok is True and message == "Enviado"
    with db.open_conn() as conn:
        row = conn.execute("SELECT destino, provider FROM email_sends").fetchone()
    assert row == ("destino@example.com", "resend")

import datetime

import db
import email_agent
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _multipart(text_plain: str, text_html: str) -> MIMEMultipart:
    message = MIMEMultipart("alternative")
    message.attach(MIMEText(text_plain, "plain", "utf-8"))
    message.attach(MIMEText(text_html, "html", "utf-8"))
    return message


def test_extract_plain_text_prefers_plain_part():
    message = _multipart("Hola, me interesa.", "<p>Hola, <b>me interesa</b>.</p>")
    assert email_agent._extract_plain_text(message) == "Hola, me interesa."


def test_extract_plain_text_strips_html_when_no_plain():
    message = MIMEText("<p>Hola, <b>me interesa</b>.</p>", "html", "utf-8")
    assert email_agent._extract_plain_text(message) == "Hola, me interesa."


def test_auto_reply_and_opt_out_detection():
    auto = MIMEText("Fuera de oficina", "plain", "utf-8")
    auto["Auto-Submitted"] = "auto-replied"
    assert email_agent._is_auto_reply(auto) is True

    normal = MIMEText("Hola", "plain", "utf-8")
    assert email_agent._is_auto_reply(normal) is False

    assert email_agent._is_opt_out("Por favor no me interesa, gracias") is True
    assert email_agent._is_opt_out("Cuéntame más de la propuesta") is False


def _seed_lead(conn, nombre, **overrides):
    values = {
        "nombre": nombre,
        "ciudad": "Bogotá",
        "estado": "Contactado",
        "email": f"{nombre.casefold()}@example.com",
        "ultima_interaccion": "2026-01-01 10:00",
        "follow_ups_sent": 0,
    }
    values.update(overrides)
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    conn.execute(
        f"INSERT INTO leads ({columns}) VALUES ({placeholders})", tuple(values.values())
    )


def test_due_follow_ups_filters_by_state_email_and_wait(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "agent.db"))
    db.init_db()
    recent = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    old = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M")

    with db.open_conn() as conn:
        _seed_lead(conn, "Vencido", ultima_interaccion=old)
        _seed_lead(conn, "Reciente", ultima_interaccion=recent)
        _seed_lead(conn, "Interesado", estado="Interesado", ultima_interaccion=old)
        _seed_lead(conn, "SinEmail", email="", ultima_interaccion=old)
        _seed_lead(conn, "NoContactar", estado_contacto="no_contactar", ultima_interaccion=old)
        _seed_lead(conn, "AlMaximo", follow_ups_sent=2, ultima_interaccion=old)

    due = email_agent._due_follow_up_leads()

    assert [lead["nombre"] for lead in due] == ["Vencido"]


def test_send_follow_ups_increments_and_waits_again(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "agent2.db"))
    db.init_db()
    old = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M")
    with db.open_conn() as conn:
        _seed_lead(conn, "Vencido", ultima_interaccion=old)

    sent_calls = []

    def _fake_send(to_email, subject, body, html=True, in_reply_to=None):
        sent_calls.append((to_email, subject))
        return True, "ok"

    monkeypatch.setattr(email_agent, "send_email", _fake_send)

    assert email_agent.send_follow_ups() == 1
    assert len(sent_calls) == 1
    assert sent_calls[0][0] == "vencido@example.com"

    with db.open_conn() as conn:
        row = conn.execute(
            "SELECT follow_ups_sent FROM leads WHERE nombre = 'Vencido'"
        ).fetchone()
    assert row[0] == 1

    assert email_agent.send_follow_ups() == 0

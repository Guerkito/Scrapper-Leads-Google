"""Agente de correo de Onyx: responde a las respuestas entrantes (IMAP) y
envía follow-ups automáticos a leads contactados que no respondieron.

Se ejecuta como proceso independiente, igual que webhook.py:

    python email_agent.py
"""

from __future__ import annotations

import datetime
import email
import hashlib
import imaplib
import re
import sqlite3
import threading
import time
from email.header import decode_header, make_header
from email.utils import parseaddr

from bs4 import BeautifulSoup
from loguru import logger

from config import (
    AUTO_OPTIMIZE,
    CALCOM_API_KEY,
    CALCOM_LINK,
    FOLLOW_UP_DAYS,
    FOLLOW_UP_MAX,
    FOLLOW_UP_POLL_MINUTES,
    IMAP_FOLDER,
    IMAP_HOST,
    IMAP_PASS,
    IMAP_PORT,
    IMAP_USER,
    INBOX_POLL_SECONDS,
    MEETINGS_POLL_MINUTES,
)
from db import claim_webhook_event, finish_webhook_event, init_db, open_conn
from services.assistant import ask_local_assistant
from services.campaign_analytics import auto_optimize
from services.email_service import send_email
from services.meetings import sync_meetings


logger.add("data/logs/email_agent.log", rotation="10 MB", level="INFO")

FOLLOW_UP_TEMPLATES = [
    "Hola {nombre}, te escribí hace unos días sobre {nicho} y quería asegurarme "
    "de que te llegó. ¿Te viene bien una llamada de 10 minutos esta semana?{link}",
    "Hola {nombre}, cierro el tema por mi parte: si en algún momento quieres "
    "mejorar {nicho}, aquí estoy. ¿Agendamos 10 minutos?{link}",
]

OPT_OUT_MARKERS = (
    "no me interesa", "no gracias", "desuscrib", "unsubscribe", "remove me",
)

FOLLOW_UP_BATCH = 25


def _header(value) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(str(value)))).strip()
    except Exception:
        return str(value).strip()


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    return re.sub(r"\s+([.,;:!?])", r"\1", text)


def _extract_plain_text(message) -> str:
    """Saca el texto del correo: prefiere text/plain; si no, limpia el HTML."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() == "text" and part.get_content_subtype() == "plain":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace").strip()[:4000]
        for part in message.walk():
            if part.get_content_subtype() == "html":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return _html_to_text(payload.decode(charset, errors="replace"))[:4000]
        return ""
    payload = message.get_payload(decode=True) or b""
    charset = message.get_content_charset() or "utf-8"
    text = payload.decode(charset, errors="replace")
    if message.get_content_subtype() == "html":
        return _html_to_text(text)[:4000]
    return text.strip()[:4000]


def _is_auto_reply(message) -> bool:
    """Evita bucles con autorespondedores y listas de correo."""
    auto = (message.get("Auto-Submitted") or "").strip().casefold()
    if auto and auto != "no":
        return True
    if (message.get("Precedence") or "").strip().casefold() in {"bulk", "junk", "list"}:
        return True
    return bool(message.get("List-Id"))


def _is_opt_out(text: str) -> bool:
    normalized = (text or "").casefold()
    return any(marker in normalized for marker in OPT_OUT_MARKERS)


def _lead_by_email(address: str) -> dict | None:
    if not address:
        return None
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM leads WHERE lower(trim(email)) = ? LIMIT 1",
            (address.casefold(),),
        ).fetchone()
        return dict(row) if row else None


def _append_history(lead_id: int, line: str) -> None:
    with open_conn() as conn:
        row = conn.execute(
            "SELECT historial_mensajes FROM leads WHERE id = ?", (lead_id,)
        ).fetchone()
        history = ((row[0] if row else "") or "") + line
        conn.execute(
            "UPDATE leads SET historial_mensajes = ? WHERE id = ?",
            (history[-20_000:], lead_id),
        )


def _record_answer(lead_id: int, inbound: str, answer: str) -> None:
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open_conn() as conn:
        conn.execute(
            "UPDATE leads SET estado = 'Interesado', ultima_interaccion = ? WHERE id = ?",
            (stamp, lead_id),
        )
        conn.execute(
            "INSERT INTO bot_logs (mensaje) VALUES (?)",
            (f"Respuesta email enviada -> lead {lead_id}",),
        )
    _append_history(lead_id, f"\nUsuario: {inbound[:1500]}\nOnyx (email): {answer}")


def _record_opt_out(lead_id: int, inbound: str) -> None:
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open_conn() as conn:
        conn.execute(
            "UPDATE leads SET estado = 'Descartado', estado_contacto = 'no_contactar', "
            "ultima_interaccion = ? WHERE id = ?",
            (stamp, lead_id),
        )
        conn.execute(
            "INSERT INTO bot_logs (mensaje) VALUES (?)",
            (f"Opt-out recibido por email -> lead {lead_id}",),
        )
    _append_history(lead_id, f"\nUsuario: {inbound[:1500]}\nSistema: opt-out registrado")
    logger.info(f"Opt-out registrado para lead {lead_id}")


def _mark_seen(imap, num) -> None:
    try:
        imap.store(num, "+FLAGS", "\\Seen")
    except Exception as exc:
        logger.warning(f"No se pudo marcar como leído {num!r}: {exc}")


def _handle_reply(message, uid: str) -> None:
    sender = parseaddr(_header(message.get("From")))[1].casefold()
    if not sender or (IMAP_USER and sender == IMAP_USER.casefold()):
        return
    text = _extract_plain_text(message)
    if not text:
        return

    message_id = (message.get("Message-ID") or "").strip()
    event_id = message_id or (
        "imap:"
        + hashlib.sha256(f"{uid}:{sender}:{text[:200]}".encode("utf-8")).hexdigest()[:32]
    )
    if not claim_webhook_event(event_id):
        return

    lead = _lead_by_email(sender)
    if not lead:
        logger.info(f"Respuesta de remitente desconocido ignorada: {sender}")
        finish_webhook_event(event_id, "ignored")
        return

    if _is_opt_out(text):
        _record_opt_out(lead["id"], text)
        finish_webhook_event(event_id, "done")
        return

    answer = ask_local_assistant(lead, text, channel="email")
    subject = _header(message.get("Subject")) or "Tu mensaje"
    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    ok, error = send_email(
        sender, reply_subject, answer, html=False, in_reply_to=message_id or None
    )
    if not ok:
        finish_webhook_event(event_id, "error", str(error)[:500])
        return
    _record_answer(lead["id"], text, answer)
    finish_webhook_event(event_id, "done")


def poll_inbox() -> int:
    """Procesa las respuestas nuevas de la bandeja. Devuelve cuántas revisó."""
    if not IMAP_USER or not IMAP_PASS:
        return 0
    processed = 0
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=30)
    try:
        imap.login(IMAP_USER, IMAP_PASS)
        imap.select(IMAP_FOLDER)
        status, data = imap.search(None, "UNSEEN")
        if status != "OK":
            return 0
        for num in (data[0] or b"").split():
            try:
                status, fetched = imap.fetch(num, "(RFC822)")
                if status != "OK" or not fetched or not isinstance(fetched[0], tuple):
                    continue
                message = email.message_from_bytes(fetched[0][1])
                if _is_auto_reply(message):
                    _mark_seen(imap, num)
                    continue
                _handle_reply(message, num.decode(errors="replace"))
                _mark_seen(imap, num)
                processed += 1
            except Exception as exc:
                logger.error(f"Error procesando correo {num!r}: {exc}")
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    return processed


def _due_follow_up_leads(
    max_follow_ups: int | None = None, days: int | None = None
) -> list[dict]:
    limit = FOLLOW_UP_MAX if max_follow_ups is None else max_follow_ups
    wait_days = FOLLOW_UP_DAYS if days is None else days
    if limit <= 0:
        return []
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM leads
            WHERE estado = 'Contactado'
              AND lower(trim(COALESCE(estado_contacto, ''))) != 'no_contactar'
              AND lower(trim(COALESCE(email, ''))) LIKE '%_@_%._%'
              AND COALESCE(follow_ups_sent, 0) < ?
              AND COALESCE(ultima_interaccion, fecha_ultimo_contacto) IS NOT NULL
              AND datetime(COALESCE(ultima_interaccion, fecha_ultimo_contacto))
                  <= datetime('now', ?)
            LIMIT ?
            """,
            (limit, f"-{int(wait_days)} days", FOLLOW_UP_BATCH),
        ).fetchall()
    return [dict(row) for row in rows]


def _follow_up_body(lead: dict, index: int) -> str:
    template = FOLLOW_UP_TEMPLATES[min(index, len(FOLLOW_UP_TEMPLATES) - 1)]
    link = f" Puedes agendar aquí: {CALCOM_LINK}" if CALCOM_LINK else ""
    return template.format(
        nombre=str(lead.get("nombre") or "hola")[:80],
        nicho=str(lead.get("nicho") or "tu negocio")[:80],
        link=link,
    )


def send_follow_ups() -> int:
    """Manda el siguiente toque a los leads contactados sin respuesta."""
    sent = 0
    for lead in _due_follow_up_leads():
        index = int(lead.get("follow_ups_sent") or 0)
        subject = f"Seguimiento · {str(lead.get('nombre') or 'tu negocio')[:60]}"
        body = _follow_up_body(lead, index)
        ok, error = send_email(lead["email"], subject, body, html=False)
        if not ok:
            logger.error(f"Follow-up falló para lead {lead['id']}: {error}")
            continue
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open_conn() as conn:
            conn.execute(
                "UPDATE leads SET ultima_interaccion = ?, "
                "follow_ups_sent = COALESCE(follow_ups_sent, 0) + 1 WHERE id = ?",
                (stamp, lead["id"]),
            )
            conn.execute(
                "INSERT INTO bot_logs (mensaje) VALUES (?)",
                (f"Follow-up email {index + 1} -> lead {lead['id']}",),
            )
        _append_history(lead["id"], f"\nOnyx (seguimiento {index + 1}): {body}")
        sent += 1
    return sent


def _inbox_loop() -> None:
    while True:
        try:
            count = poll_inbox()
            if count:
                logger.info(f"Bandeja: {count} correo(s) procesado(s)")
        except Exception as exc:
            logger.error(f"Bandeja: error de conexión ({exc})")
        time.sleep(INBOX_POLL_SECONDS)


def _follow_up_loop() -> None:
    while True:
        try:
            sent = send_follow_ups()
            if sent:
                logger.info(f"Follow-ups enviados: {sent}")
            if AUTO_OPTIMIZE:
                actions = auto_optimize()
                paused = [action for action in actions if action["action"] == "pausar"]
                if paused:
                    logger.info(f"Auto-optimización: {len(paused)} segmento(s) pausado(s)")
        except Exception as exc:
            logger.error(f"Follow-ups: error ({exc})")
        time.sleep(FOLLOW_UP_POLL_MINUTES * 60)


def _meetings_loop() -> None:
    while True:
        try:
            result = sync_meetings()
            if result.get("confirmed") or result.get("reverted") or result.get("errors"):
                logger.info(f"Reuniones: {result}")
        except Exception as exc:
            logger.error(f"Reuniones: error ({exc})")
        time.sleep(MEETINGS_POLL_MINUTES * 60)


def main() -> None:
    init_db()
    if not IMAP_USER or not IMAP_PASS:
        logger.warning(
            "IMAP sin credenciales: configura IMAP_USER/IMAP_PASS o EMAIL_USER/EMAIL_PASS. "
            "El respondedor automático queda apagado."
        )
    if FOLLOW_UP_MAX <= 0:
        logger.info("FOLLOW_UP_MAX=0: seguimientos desactivados.")
    if not CALCOM_API_KEY:
        logger.info("Sin CALCOM_API_KEY: la confirmación de reuniones queda apagada.")
    threading.Thread(target=_inbox_loop, daemon=True, name="onyx-inbox").start()
    threading.Thread(target=_follow_up_loop, daemon=True, name="onyx-followup").start()
    if CALCOM_API_KEY:
        threading.Thread(target=_meetings_loop, daemon=True, name="onyx-meetings").start()
    logger.info("Agente de email Onyx activo (respuestas IMAP + follow-ups + reuniones). Ctrl+C para salir.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Agente de email detenido.")


if __name__ == "__main__":
    main()

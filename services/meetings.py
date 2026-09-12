"""Confirmación de reuniones con la agenda de Cal.com.

Consulta la API v2 por el email del lead y actualiza su estado:
- reserva próxima → estado "Reunión" + fecha y enlace
- sin reserva y estaba en "Reunión" → vuelve a "Interesado" (canceló o ya pasó)

No necesita webhooks ni URL pública: es una consulta saliente.
"""

from __future__ import annotations

import datetime
import sqlite3

import requests
from loguru import logger

from config import CALCOM_API_KEY, CALCOM_API_VERSION, MEETINGS_BATCH
from db import open_conn


API_BOOKINGS = "https://api.cal.com/v2/bookings"
ACTIVE_STATES = ("Interesado", "Reunión")


def fetch_upcoming(email: str) -> dict | None:
    """Primera reserva próxima asociada a ese email, o None."""
    response = requests.get(
        API_BOOKINGS,
        params={"attendeeEmail": email, "status": "upcoming"},
        headers={
            "Authorization": f"Bearer {CALCOM_API_KEY}",
            "cal-api-version": CALCOM_API_VERSION,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json().get("data")
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None
    bookings = [item for item in data if isinstance(item, dict)]
    return bookings[0] if bookings else None


def booking_fields(booking: dict) -> tuple[str, str]:
    """(fecha legible, enlace de la videollamada) de una reserva."""
    start = str(booking.get("start") or "").replace("T", " ")[:16]
    url = str(booking.get("meetingUrl") or booking.get("location") or "").strip()
    if not url.startswith("http"):
        url = ""
    return start, url[:300]


def _candidates(limit: int) -> list[dict]:
    with open_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, nombre, email, estado FROM leads
            WHERE estado IN ('Interesado', 'Reunión')
              AND email LIKE '%@%'
            ORDER BY CASE WHEN estado = 'Reunión' THEN 0 ELSE 1 END, id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


def sync_meetings(limit: int | None = None) -> dict:
    """Marca reuniones confirmadas y revierte las canceladas."""
    if not CALCOM_API_KEY:
        return {"skipped": True, "checked": 0, "confirmed": 0, "reverted": 0, "errors": 0}

    batch = MEETINGS_BATCH if limit is None else max(1, int(limit))
    checked = confirmed = reverted = errors = 0
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    for lead in _candidates(batch):
        try:
            booking = fetch_upcoming(lead["email"])
        except Exception as exc:
            errors += 1
            logger.warning(f"Cal.com: fallo consultando {lead['nombre']} ({exc})")
            if checked == 0 and errors >= 3:
                logger.error("Cal.com: varias consultas fallidas seguidas; abortando el ciclo.")
                break
            continue
        checked += 1

        if booking:
            start, url = booking_fields(booking)
            with open_conn() as conn:
                conn.execute(
                    "UPDATE leads SET estado = 'Reunión', reunion_at = ?, reunion_url = ?, "
                    "ultima_interaccion = ? WHERE id = ?",
                    (start or None, url or None, stamp, lead["id"]),
                )
            if lead["estado"] != "Reunión":
                confirmed += 1
                logger.info(f"Reunión confirmada: {lead['nombre']} · {start or 'sin fecha'}")
        elif lead["estado"] == "Reunión":
            with open_conn() as conn:
                conn.execute(
                    "UPDATE leads SET estado = 'Interesado', reunion_at = NULL, "
                    "reunion_url = NULL WHERE id = ?",
                    (lead["id"],),
                )
            reverted += 1
            logger.info(f"Reunión revertida (cancelada o pasada): {lead['nombre']}")

    return {
        "skipped": False,
        "checked": checked,
        "confirmed": confirmed,
        "reverted": reverted,
        "errors": errors,
    }

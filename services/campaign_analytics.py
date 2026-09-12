"""Métricas por campaña/segmento y optimización automática (pausa/escala).

Consultas SQLite puras (sin Streamlit ni pandas) para que también pueda usarlas
el agente de email en segundo plano.
"""

from __future__ import annotations

from loguru import logger

from config import COST_PER_EMAIL, OPTIMIZE_MIN_LEADS, OPTIMIZE_SCALE_RATE
from db import open_conn


def paused_segment_keys(product_key: str | None = None) -> set[tuple[str, str]]:
    query = "SELECT product_key, segment_key FROM segment_status WHERE status = 'paused'"
    params: tuple = ()
    if product_key:
        query += " AND product_key = ?"
        params = (product_key,)
    with open_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return {(row[0], row[1]) for row in rows}


def set_segment_status(
    product_key: str, segment_key: str, status: str, reason: str = ""
) -> None:
    with open_conn() as conn:
        conn.execute(
            """
            INSERT INTO segment_status (product_key, segment_key, status, reason, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(product_key, segment_key) DO UPDATE SET
                status = excluded.status,
                reason = excluded.reason,
                updated_at = CURRENT_TIMESTAMP
            """,
            (product_key, segment_key, status, reason[:300]),
        )


def campaign_performance(
    cost_per_email: float | None = None,
    min_leads: int | None = None,
    scale_rate: float | None = None,
) -> list[dict]:
    """Una fila por oportunidad (campaña + segmento) con sus métricas reales."""
    price = COST_PER_EMAIL if cost_per_email is None else cost_per_email
    lead_floor = OPTIMIZE_MIN_LEADS if min_leads is None else min_leads
    reply_goal = OPTIMIZE_SCALE_RATE if scale_rate is None else scale_rate
    paused = paused_segment_keys()

    with open_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                o.product_key,
                MAX(o.product_label) AS product_label,
                o.segment_key,
                MAX(o.segment_label) AS segment_label,
                COUNT(DISTINCT o.lead_id) AS leads,
                SUM(CASE WHEN l.estado IN ('Contactado', 'Interesado', 'Cerrado')
                         THEN 1 ELSE 0 END) AS contactados,
                SUM(CASE WHEN l.estado IN ('Interesado', 'Cerrado', 'Reunión')
                          OR COALESCE(l.historial_mensajes, '') LIKE '%Usuario:%'
                         THEN 1 ELSE 0 END) AS respondieron,
                SUM(CASE WHEN l.estado = 'Cerrado' THEN 1 ELSE 0 END) AS cerrados,
                SUM(CASE WHEN l.estado = 'Reunión' THEN 1 ELSE 0 END) AS reuniones,
                COALESCE(SUM((
                    SELECT COUNT(*) FROM email_sends s
                    WHERE lower(trim(s.destino)) = lower(trim(l.email))
                )), 0) AS emails
            FROM lead_opportunities o
            JOIN leads l ON l.id = o.lead_id
            WHERE o.segment_key != ''
            GROUP BY o.product_key, o.segment_key
            """
        ).fetchall()

    results = []
    for row in rows:
        (product_key, product_label, segment_key, segment_label,
         leads, contactados, respondieron, cerrados, reuniones, emails) = row
        leads = int(leads or 0)
        contactados = int(contactados or 0)
        respondieron = int(respondieron or 0)
        emails = int(emails or 0)
        reply_rate = respondieron / leads if leads else 0.0
        cost = emails * price
        if leads >= lead_floor and contactados > 0 and respondieron == 0:
            recommendation = "pausar"
        elif respondieron >= 2 and reply_rate >= reply_goal:
            recommendation = "escalar"
        else:
            recommendation = "mantener"
        results.append({
            "product_key": product_key,
            "product_label": product_label or product_key,
            "segment_key": segment_key,
            "segment_label": segment_label or segment_key,
            "leads": leads,
            "contactados": contactados,
            "respondieron": respondieron,
            "cerrados": cerrados or 0,
            "reuniones": int(reuniones or 0),
            "emails": emails,
            "tasa_respuesta": reply_rate,
            "coste_estimado": cost,
            "coste_por_lead": (cost / leads) if leads else 0.0,
            "estado": "pausado" if (product_key, segment_key) in paused else "activo",
            "recomendacion": recommendation,
        })
    return results


def auto_optimize(
    min_leads: int | None = None, scale_rate: float | None = None
) -> list[dict]:
    """Pausa segmentos sin respuesta y reporta los que conviene escalar.

    Nunca reanuda automáticamente: eso queda para el panel.
    """
    actions = []
    for row in campaign_performance(min_leads=min_leads, scale_rate=scale_rate):
        if row["recomendacion"] == "pausar" and row["estado"] == "activo":
            set_segment_status(
                row["product_key"], row["segment_key"], "paused",
                f"Sin respuestas tras {row['leads']} leads contactados",
            )
            logger.info(
                f"Auto-optimización: segmento pausado {row['product_key']}/{row['segment_key']}"
            )
            actions.append({**row, "action": "pausar", "applied": True})
            row["estado"] = "pausado"
        elif row["recomendacion"] == "escalar":
            actions.append({**row, "action": "escalar", "applied": False})
    return actions


def send_summary(cost_per_email: float | None = None) -> dict:
    """Totales de envío y respuesta para los KPI del panel."""
    price = COST_PER_EMAIL if cost_per_email is None else cost_per_email
    with open_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM email_sends").fetchone()[0] or 0
        today = conn.execute(
            "SELECT COUNT(*) FROM email_sends WHERE date(created_at) = date('now')"
        ).fetchone()[0] or 0
        lead_row = conn.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN estado IN ('Interesado', 'Cerrado', 'Reunión')
                             OR COALESCE(historial_mensajes, '') LIKE '%Usuario:%'
                            THEN 1 ELSE 0 END),
                   SUM(CASE WHEN estado = 'Reunión' THEN 1 ELSE 0 END)
            FROM leads
            """
        ).fetchone()
    leads_total = int(lead_row[0] or 0)
    respondieron = int(lead_row[1] or 0)
    reuniones = int(lead_row[2] or 0)
    return {
        "total": int(total),
        "hoy": int(today),
        "coste_total": int(total) * price,
        "leads": leads_total,
        "respondieron": respondieron,
        "reuniones": reuniones,
        "tasa_respuesta": (respondieron / leads_total) if leads_total else 0.0,
    }

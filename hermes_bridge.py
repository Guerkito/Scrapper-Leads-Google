import sys
import json
import argparse
import sqlite3
from db import open_conn, update_lead_field

def get_lead_info(query):
    """Busca información de un lead por teléfono o nombre."""
    conn = open_conn()
    try:
        conn.row_factory = sqlite3.Row

        # Preferir coincidencias exactas sobre parciales para no devolver un lead
        # arbitrario cuando el prefijo coincide con varios teléfonos.
        cursor = conn.execute(
            """
            SELECT * FROM leads
            WHERE telefono LIKE ? OR whatsapp_id = ? OR nombre LIKE ?
            ORDER BY CASE
                WHEN telefono = ? OR whatsapp_id = ? OR nombre = ? THEN 0
                ELSE 1
            END, id
            LIMIT 1
            """,
            (f"%{query}%", query, f"%{query}%", query, query, query)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def update_lead(lead_id, field, value):
    """Actualiza un campo de un lead."""
    success = update_lead_field(lead_id, field, value)
    return {"success": success}

def list_recent_leads(limit=5):
    """Lista los leads más recientes."""
    conn = open_conn()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT id, nombre, telefono, ciudad, nicho, estado FROM leads ORDER BY fecha_captura DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        return rows
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hermes-Onyx Bridge")
    subparsers = parser.add_subparsers(dest="command")

    # Get lead
    get_p = subparsers.add_parser("get_lead")
    get_p.add_argument("query", help="Teléfono, WhatsApp ID o Nombre")

    # Update lead
    up_p = subparsers.add_parser("update_lead")
    up_p.add_argument("id", type=int)
    up_p.add_argument("field")
    up_p.add_argument("value")

    # List leads
    list_p = subparsers.add_parser("list_leads")
    list_p.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    if args.command == "get_lead":
        result = get_lead_info(args.query)
        print(json.dumps(result, indent=2, default=str))
    elif args.command == "update_lead":
        result = update_lead(args.id, args.field, args.value)
        print(json.dumps(result))
    elif args.command == "list_leads":
        result = list_recent_leads(args.limit)
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()

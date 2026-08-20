"""Regresiones de los bugs corregidos (formatos locales, redirecciones, etc.)."""

import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db
from db import _coerce_float, _coerce_reviews
from engine.maps_helpers import decode_google_url
from sources.base_source import Lead


def test_coerce_float_local_formats():
    assert _coerce_float("4,5") == 4.5
    assert _coerce_float("4.5/5") == 4.5
    assert _coerce_float(4.8) == 4.8
    assert _coerce_float(None) == 0.0
    assert _coerce_float("sin rating") == 0.0


def test_coerce_reviews_local_formats():
    assert _coerce_reviews("1,200") == 1200
    assert _coerce_reviews("1.234") == 1234
    assert _coerce_reviews("2,5 mil") == 2500
    assert _coerce_reviews(1200.0) == 1200
    assert _coerce_reviews("120 reseñas") == 120
    assert _coerce_reviews(None) == 0


def test_merge_survives_local_formats(tmp_path):
    """El enriquecimiento no debe descartarse por rating '4,5' o reseñas '1,200'."""
    db.DB_PATH = str(tmp_path / "formats.db")
    db.init_db()
    conn = db.open_conn()

    first = Lead("Clinica Local", "Bogotá", "Salud", "google_maps", pais="Colombia",
                 telefono="3001234567", rating=4.5, reseñas=1200)
    second = Lead("Clinica Local", "Bogotá", "Salud", "doctoralia", pais="Colombia",
                  email="contacto@clinica.co")

    assert db.save_lead(first, conn) == 1
    assert db.save_lead(second, conn) == 0  # se fusiona, no falla

    conn.row_factory = db.sqlite3.Row
    row = dict(conn.execute("SELECT * FROM leads").fetchone())
    conn.close()

    assert row["email"] == "contacto@clinica.co"
    assert row["rating"] == 4.5
    assert row["reseñas"] == 1200


def test_decode_google_redirect():
    encoded = (
        "https://www.google.com/url?q=https%3A%2F%2Fco.computrabajo.com%2Fempresas%2Fperfil%2Facme"
        "&sa=U&ved=2ahUKEwiZ"
    )
    assert decode_google_url(encoded) == "https://co.computrabajo.com/empresas/perfil/acme"
    # Las URLs normales no se tocan
    assert decode_google_url("https://www.facebook.com/acme") == "https://www.facebook.com/acme"
    assert decode_google_url(None) is None


def test_merge_with_local_rating_string_on_existing_row(tmp_path):
    """Un rating guardado como '4,5' en la DB no debe romper el merge posterior."""
    db.DB_PATH = str(tmp_path / "formats2.db")
    db.init_db()
    conn = db.open_conn()

    first = Lead("Ferreteria XYZ", "Medellín", "Ferreterías", "google_maps", pais="Colombia")
    assert db.save_lead(first, conn) == 1
    # Simular un valor legacy con formato local guardado directamente
    conn.execute("UPDATE leads SET rating='4,5', reseñas='1,200' WHERE nombre='Ferreteria XYZ'")
    conn.commit()

    enrichment = Lead("Ferreteria XYZ", "Medellín", "Ferreterías", "paginas_amarillas",
                      pais="Colombia", email="ventas@ferreteria.com", rating=4.7, reseñas=1500)
    assert db.save_lead(enrichment, conn) == 0
    conn.row_factory = db.sqlite3.Row
    row = dict(conn.execute("SELECT * FROM leads").fetchone())
    conn.close()
    assert row["email"] == "ventas@ferreteria.com"
    assert row["rating"] == 4.7
    assert row["reseñas"] == 1500

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

import db
import services.leads as lead_service
import services.whatsapp_service as whatsapp_service
import ui.crm as crm_ui
from services.search_mission import SearchMission


def _ui_leads():
    return pd.DataFrame([{
        "id": 1,
        "nombre": "Empresa de prueba",
        "ciudad": "Bogotá",
        "departamento": "Bogotá D.C.",
        "pais": "Colombia",
        "nicho": "Restaurantes",
        "sector": "Servicios",
        "tipo": "B2C",
        "product_keys": "divi_restaurantes",
        "productos_objetivo": "DIVI · Restaurantes",
        "producto_principal": "DIVI · Restaurantes",
        "campaign_key_principal": "divi_restaurantes",
        "segmentos_objetivo": "Restaurantes",
        "segmento_principal": "Restaurantes",
        "fit_score": 92,
        "motivo_afinidad": "Restaurante con servicio en mesa",
        "decisor_objetivo": "Gerente o propietario",
        "pitch_sugerido": "Agilizar el pago y la división de la cuenta desde la mesa.",
        "estado": "Nuevo",
        "estado_contacto": "sin_contactar",
        "calificacion": "oro",
        "telefono": "3001234567",
        "telefono_e164": "+573001234567",
        "rating": 4.7,
        "reseñas": 80,
        "tiene_web": False,
        "sitio_web": "",
        "maps_url": "https://maps.google.com/?cid=1",
        "place_id": "place-1",
        "perfil_url": "",
        "email": "",
        "instagram": "",
        "facebook": "",
        "linkedin_empresa": "",
        "pixel_fb": False,
        "pixel_google": False,
        "nit": "",
        "representante_legal": "",
        "fuente": "google_maps",
        "fuentes_encontrado": "[]",
        "fecha_captura": "2026-07-24",
        "notas": "",
        "lat": 4.65,
        "lng": -74.05,
        "zona": "Centro",
    }])


def test_update_lead_field_invalidates_cached_dataframe(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "cache.db"))
    db.init_db()
    with db.open_conn() as conn:
        lead_id = conn.execute(
            "INSERT INTO leads(nombre, estado) VALUES ('Acme', 'Nuevo')"
        ).lastrowid

    invalidations = []
    monkeypatch.setattr(
        lead_service, "invalidate_leads_cache", lambda: invalidations.append(True)
    )

    assert db.update_lead_field(lead_id, "estado", "Contactado") is True
    assert invalidations == [True]
    with db.open_conn() as conn:
        assert conn.execute(
            "SELECT estado FROM leads WHERE id = ?", (lead_id,)
        ).fetchone()[0] == "Contactado"


def test_whatsapp_health_check_is_cached(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"instance": {"state": "open"}}

    def fake_get(url, headers, timeout):
        calls.append((url, timeout))
        return Response()

    whatsapp_service.check_whatsapp_connection.clear()
    monkeypatch.setattr(whatsapp_service.requests, "get", fake_get)
    first = whatsapp_service.check_whatsapp_connection(
        "http://evolution.test", "secret", "onyx"
    )
    second = whatsapp_service.check_whatsapp_connection(
        "http://evolution.test", "secret", "onyx"
    )
    whatsapp_service.check_whatsapp_connection.clear()

    assert first == second == {"status": "success", "message": "WhatsApp: CONECTADO"}
    assert len(calls) == 1
    assert calls[0][1] == (0.5, 1.0)


def test_search_mission_uses_plain_thread_safe_state():
    mission = SearchMission()

    def write_logs(prefix):
        for number in range(75):
            mission.add_log(f"{prefix}-{number}")

    import threading

    threads = [threading.Thread(target=write_logs, args=(str(index),)) for index in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    snapshot = mission.snapshot()
    assert len(snapshot["logs"]) == 200
    assert all(entry.startswith("[") for entry in snapshot["logs"])
    assert "st" not in vars(__import__("services.search_mission", fromlist=["st"]))


def test_search_mission_finishes_before_publishing_completion(monkeypatch, tmp_path):
    import services.search_mission as mission_service

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "mission.db"))
    db.init_db()
    invalidations = []
    monkeypatch.setattr(
        mission_service, "invalidate_leads_cache", lambda: invalidations.append(True)
    )

    class FakeOrchestrator:
        callable_phones_found = 1

        def __init__(self, _sources, log_callback, lead_callback):
            self.log_callback = log_callback
            self.lead_callback = lead_callback

        def _log(self, message):
            self.log_callback(message)

        async def buscar_todos(self, *_args, **_kwargs):
            self._log("captura")
            self.lead_callback(1, True)
            self.lead_callback(None, False)

        def stop(self):
            return None

    monkeypatch.setattr(mission_service, "Orchestrator", FakeOrchestrator)
    mission = SearchMission()
    assert mission.start(
        [], None, "Restaurantes", [{"ciudad": "Bogotá"}], False, 1, False,
        pais="Colombia",
    ) is True
    mission._thread.join(timeout=5)

    snapshot = mission.snapshot()
    assert snapshot["running"] is False
    assert snapshot["total_processed"] == 1
    assert snapshot["total_duplicates"] == 1
    assert snapshot["last_summary"] == {
        "leads": 1, "dupes": 1, "phones": 1, "error": None,
    }
    assert invalidations == [True]
    assert any("captura" in entry for entry in snapshot["logs"])


def test_navigation_runs_once_and_database_initializes_once(monkeypatch):
    st.cache_resource.clear()
    counts = {"db": 0, "whatsapp": 0}

    def fake_init_db():
        counts["db"] += 1

    def fake_whatsapp(*_args, **_kwargs):
        counts["whatsapp"] += 1
        return {"status": "info", "message": "diagnóstico"}

    monkeypatch.setattr(db, "init_db", fake_init_db)
    monkeypatch.setattr(lead_service, "load_all_leads", lambda: _ui_leads())
    monkeypatch.setattr(whatsapp_service, "check_whatsapp_connection", fake_whatsapp)

    app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=20)
    app.run()
    assert len(app.exception) == 0
    assert counts == {"db": 1, "whatsapp": 1}

    counts["db"] = counts["whatsapp"] = 0
    next(button for button in app.button if button.label == "CRM").click().run()

    assert len(app.exception) == 0
    assert counts == {"db": 0, "whatsapp": 1}
    st.cache_resource.clear()


def test_crm_offers_filtered_and_portfolio_batch_exports(monkeypatch):
    st.cache_resource.clear()
    monkeypatch.setattr(db, "init_db", lambda: None)
    monkeypatch.setattr(lead_service, "load_all_leads", _ui_leads)
    monkeypatch.setattr(
        whatsapp_service,
        "check_whatsapp_connection",
        lambda *_args, **_kwargs: {"status": "info", "message": "diagnóstico"},
    )
    deletions = []
    monkeypatch.setattr(
        crm_ui,
        "delete_portfolio_batch",
        lambda lead_ids, portfolio: (
            deletions.append((lead_ids, portfolio))
            or {
                "requested": len(lead_ids),
                "matched": len(lead_ids),
                "leads_deleted": len(lead_ids),
                "leads_preserved": 0,
                "associations_deleted": len(lead_ids),
            }
        ),
    )

    app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=20).run()
    next(button for button in app.button if button.label == "CRM").click().run()

    export_mode = next(
        radio for radio in app.radio
        if radio.label == "¿Cómo quieres organizar la descarga?"
    )
    assert export_mode.value == "filtered"
    assert next(
        button for button in app.button if button.label == "Preparar Excel"
    ).disabled is False

    export_mode.set_value("portfolio").run()
    batches = next(
        widget for widget in app.multiselect
        if widget.label == "¿Qué lotes quieres incluir?"
    )
    assert batches.value == ["divi"]
    assert next(
        button for button in app.button
        if button.label == "Preparar paquete por lotes"
    ).disabled is False

    delete_button = next(
        button for button in app.button if button.label == "Borrar lote DIVI"
    )
    assert delete_button.disabled is True
    confirmation = next(
        widget for widget in app.text_input
        if widget.label.startswith("Escribe `BORRAR DIVI`")
    )
    confirmation.set_value("BORRAR DIVI").run()
    delete_button = next(
        button for button in app.button if button.label == "Borrar lote DIVI"
    )
    assert delete_button.disabled is False
    delete_button.click().run()

    assert deletions == [([1], "divi")]
    assert any("Lote DIVI borrado" in message.value for message in app.success)
    assert len(app.exception) == 0
    st.cache_resource.clear()


def test_product_campaign_filters_search_targets(monkeypatch):
    st.cache_resource.clear()
    monkeypatch.setattr(db, "init_db", lambda: None)
    monkeypatch.setattr(lead_service, "load_all_leads", _ui_leads)
    monkeypatch.setattr(
        whatsapp_service,
        "check_whatsapp_connection",
        lambda *_args, **_kwargs: {"status": "info", "message": "diagnóstico"},
    )

    app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=20).run()
    product = next(
        widget for widget in app.selectbox
        if widget.label == "1. ¿Qué quieres vender?"
    )
    product.set_value("watson_clinic").run()

    target = next(
        widget for widget in app.multiselect
        if widget.label == "2. ¿Qué tipo de cliente buscas?"
    )
    assert target.value == ["ips_privadas", "ese_publicas"]

    target.set_value(["ese_publicas"]).run()
    objectives = next(
        widget for widget in app.multiselect
        if widget.label == "Términos automáticos"
    )
    assert objectives.value == [
        "ESE hospital", "hospital municipal", "centro de salud municipal"
    ]
    assert len(app.exception) == 0
    st.cache_resource.clear()


def test_onyx_service_campaign_configures_focused_search(monkeypatch):
    st.cache_resource.clear()
    monkeypatch.setattr(db, "init_db", lambda: None)
    monkeypatch.setattr(lead_service, "load_all_leads", _ui_leads)
    monkeypatch.setattr(
        whatsapp_service,
        "check_whatsapp_connection",
        lambda *_args, **_kwargs: {"status": "info", "message": "diagnóstico"},
    )

    app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=20).run()
    product = next(
        widget for widget in app.selectbox
        if widget.label == "1. ¿Qué quieres vender?"
    )
    product.set_value("onyx_automation").run()

    target = next(
        widget for widget in app.multiselect
        if widget.label == "2. ¿Qué tipo de cliente buscas?"
    )
    objectives = next(
        widget for widget in app.multiselect
        if widget.label == "Términos automáticos"
    )
    sources = next(
        widget for widget in app.multiselect
        if widget.label == "Dónde buscar"
    )

    assert target.value == ["operaciones"]
    assert objectives.value == [
        "empresa de logística", "empresa de transporte", "fábrica", "distribuidora"
    ]
    assert sources.value == ["Maps", "LinkedIn", "Computrabajo (B2B)"]
    assert any("Qué validar:" in markdown.value for markdown in app.markdown)
    assert len(app.exception) == 0
    st.cache_resource.clear()


def test_search_call_to_action_waits_for_a_target(monkeypatch):
    st.cache_resource.clear()
    monkeypatch.setattr(db, "init_db", lambda: None)
    monkeypatch.setattr(lead_service, "load_all_leads", _ui_leads)
    monkeypatch.setattr(
        whatsapp_service,
        "check_whatsapp_connection",
        lambda *_args, **_kwargs: {"status": "info", "message": "diagnóstico"},
    )

    app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=20).run()
    create_button = next(
        button for button in app.button if button.label == "Crear lista para llamar"
    )
    assert create_button.disabled is True

    next(button for button in app.button if button.label == "Restaurantes").click().run()
    create_button = next(
        button for button in app.button if button.label == "Crear lista para llamar"
    )
    assert create_button.disabled is False
    assert len(app.exception) == 0
    st.cache_resource.clear()

import pytest
from fastapi.testclient import TestClient

from web import auth
from web.app import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def _sin_login(monkeypatch):
    """Estos tests asumen panel abierto, aunque el .env tenga PANEL_PASSWORD."""
    monkeypatch.setattr(auth, "PANEL_PASSWORD", "")


def test_web_main_pages_render():
    for path in (
        "/", "/search", "/decisions", "/crm", "/analytics",
        "/email", "/whatsapp", "/settings", "/map", "/library", "/admin", "/help",
    ):
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"


def test_web_admin_downloads():
    export = client.get("/admin/export.csv")
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]

    backup = client.get("/admin/backup.db")
    assert backup.status_code == 200
    assert backup.headers["content-type"] == "application/octet-stream"


def test_web_map_filters_render():
    response = client.get("/map", params=[("estados", "Nuevo"), ("min_rating", "4")])
    assert response.status_code == 200
    assert "Leads en mapa" in response.text


def test_web_progress_partials_render():
    for path in ("/search/progress", "/decisions/progress", "/email/progress", "/whatsapp/progress"):
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"


def test_web_crm_search_and_lead_detail():
    response = client.get("/crm", params={"q": "a", "page": 1})
    assert response.status_code == 200

    listed = client.get("/crm")
    assert listed.status_code == 200

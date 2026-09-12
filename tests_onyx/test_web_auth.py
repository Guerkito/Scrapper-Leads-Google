import pytest
from fastapi.testclient import TestClient

from web import auth
from web.app import app


@pytest.fixture
def protected(monkeypatch):
    monkeypatch.setattr(auth, "PANEL_PASSWORD", "secreto")
    monkeypatch.setattr(auth, "SESSION_SECRET", "clave-de-prueba")
    monkeypatch.setattr(auth, "SESSION_DAYS", 1)
    auth.clear_attempts("testclient")
    client = TestClient(app)
    yield client
    auth.clear_attempts("testclient")


def test_guard_redirects_to_login(protected):
    response = protected.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_login_flow_and_logout(protected):
    bad = protected.post("/login", data={"password": "mala", "next": "/"})
    assert bad.status_code == 401

    good = protected.post(
        "/login", data={"password": "secreto", "next": "/crm"}, follow_redirects=False
    )
    assert good.status_code == 303
    assert good.headers["location"] == "/crm"

    page = protected.get("/")
    assert page.status_code == 200
    assert "Cerrar sesión" in page.text

    logout = protected.get("/logout", follow_redirects=False)
    assert logout.status_code == 303
    assert protected.get("/", follow_redirects=False).status_code == 303


def test_token_roundtrip(monkeypatch):
    monkeypatch.setattr(auth, "SESSION_SECRET", "clave")
    monkeypatch.setattr(auth, "SESSION_DAYS", 1)

    assert auth.verify_token(auth.make_token())
    assert not auth.verify_token("123.deadbeef")
    assert not auth.verify_token("no-es-un-token")
    assert not auth.verify_token(None)


def test_login_rate_limit(protected):
    for _ in range(auth.MAX_ATTEMPTS):
        protected.post("/login", data={"password": "mala"})

    blocked = protected.post("/login", data={"password": "secreto"})
    assert blocked.status_code == 429


def test_open_redirect_is_blocked(protected):
    response = protected.post(
        "/login",
        data={"password": "secreto", "next": "//evil.com"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_csrf_blocks_foreign_origin(protected):
    protected.post("/login", data={"password": "secreto"})

    response = protected.post(
        "/search/save",
        data={"favorite_name": "x"},
        headers={"Origin": "http://evil.com"},
    )
    assert response.status_code == 403

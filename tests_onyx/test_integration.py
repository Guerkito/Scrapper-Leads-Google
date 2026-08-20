import sys
import os
import asyncio
import tempfile
from unittest.mock import MagicMock, AsyncMock
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.orchestrator import Orchestrator
from sources.base_source import BaseSource, Lead
import db

# Mock DB
TEST_DB = os.path.join(tempfile.gettempdir(), "onyx_test_integration.db")
db.DB_PATH = TEST_DB

pytestmark = pytest.mark.anyio

@pytest.fixture
def anyio_backend():
    return "asyncio"

def cleanup_test_db():
    db.DB_PATH = TEST_DB
    for path in (TEST_DB, f"{TEST_DB}-wal", f"{TEST_DB}-shm"):
        if os.path.exists(path):
            os.remove(path)

class MockSource(BaseSource):
    def __init__(self, name, mock_leads):
        self.name = name
        self.mock_leads = mock_leads
        
    async def buscar(self, query: str, ciudad: str, **kwargs) -> list[Lead]:
        print(f"Mock {self.name} buscando {query}...")
        await asyncio.sleep(0.1) # Simular latencia
        lead_callback = kwargs.get("lead_callback")
        if lead_callback:
            for lead in self.mock_leads:
                lead_callback(lead)
        return self.mock_leads


class AdaptivePhoneSource(BaseSource):
    def __init__(self, phones):
        self.phones = phones
        self.calls = []

    async def buscar(self, query: str, ciudad: str, **kwargs) -> list[Lead]:
        self.calls.append(query)
        lead = Lead(
            nombre=f"Negocio {query}",
            ciudad=ciudad,
            nicho=query,
            fuente="adaptive",
            telefono=self.phones[query],
        )
        callback = kwargs.get("lead_callback")
        accepted = callback(lead) if callback else True
        return [lead] if accepted is not False else []

async def test_integration_flow():
    db.DB_PATH = TEST_DB
    cleanup_test_db()
    db.init_db()

    # Preparar leads mock
    lead1 = Lead(nombre="Restaurante ABC", ciudad="Bogota", nicho="Restaurantes", fuente="mock1", telefono="123")
    lead2 = Lead(nombre="Restaurante ABC", ciudad="Bogota", nicho="Restaurantes", fuente="mock2", email="abc@test.com")
    
    source1 = MockSource("Source1", [lead1])
    source2 = MockSource("Source2", [lead2])
    
    # El orquestador usa playwright pero nosotros mockearemos la parte que usa playwright si es posible 
    # o simplemente dejaremos que el orquestador cree el browser pero las fuentes no lo usen.
    
    # Mock Playwright
    import engine.orchestrator
    from unittest.mock import AsyncMock
    
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser
    
    # Mockear el context manager de async_playwright
    mock_playwright_cm = AsyncMock()
    mock_playwright_cm.__aenter__.return_value = mock_playwright
    
    engine.orchestrator.async_playwright = MagicMock(return_value=mock_playwright_cm)

    async def mock_expandir_query(query):
        return [query]

    engine.orchestrator.expandir_query = mock_expandir_query
    
    orch = Orchestrator(fuentes=[source1, source2])
    
    print("🚀 Ejecutando orquestador...")
    results = await orch.buscar_todos("Restaurantes", ["Bogota"])
    
    assert len(results) == 2
    
    # Verificar en DB
    conn = db.open_conn()
    cursor = conn.execute("SELECT nombre, email FROM leads WHERE nombre='Restaurante ABC'")
    row = cursor.fetchone()
    assert row is not None
    assert row[1] == "abc@test.com"
    conn.close()
    
    cleanup_test_db()

    print("✅ Integration Test (Orquestador) PASSED")

async def test_hunter_mode_only_persists_leads_without_website():
    db.DB_PATH = TEST_DB
    cleanup_test_db()
    db.init_db()

    lead_without_web = Lead(
        nombre="Negocio Sin Web",
        ciudad="Bogota",
        nicho="Restaurantes",
        fuente="mock",
        telefono="123",
        sitio_web=None,
        tiene_web=False
    )
    lead_with_web = Lead(
        nombre="Negocio Con Web",
        ciudad="Bogota",
        nicho="Restaurantes",
        fuente="mock",
        telefono="456",
        sitio_web="https://negocioconweb.com",
        tiene_web=True
    )

    import engine.orchestrator

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    mock_playwright_cm = AsyncMock()
    mock_playwright_cm.__aenter__.return_value = mock_playwright

    engine.orchestrator.async_playwright = MagicMock(return_value=mock_playwright_cm)

    async def mock_expandir_query(query):
        return [query]

    engine.orchestrator.expandir_query = mock_expandir_query

    orch = Orchestrator(fuentes=[MockSource("SourceHunter", [lead_without_web, lead_with_web])])
    results = await orch.buscar_todos("Restaurantes", ["Bogota"], hunter_mode=True)

    assert [lead.nombre for lead in results] == ["Negocio Sin Web"]

    conn = db.open_conn()
    rows = conn.execute("SELECT nombre, sitio_web, tiene_web FROM leads ORDER BY nombre").fetchall()
    conn.close()

    assert rows == [("Negocio Sin Web", None, 0)]

    cleanup_test_db()


async def test_cold_call_mode_expands_only_until_unique_valid_phone_target(monkeypatch):
    db.DB_PATH = TEST_DB
    cleanup_test_db()
    db.init_db()
    monkeypatch.setattr("engine.orchestrator.random.uniform", lambda *_: 0)

    source = AdaptivePhoneSource({
        "q1": "sin teléfono",
        "q2": "300 123 4567",
        "q3": "+57 301 234 5678",
        "q4": "+57 302 345 6789",
    })
    callable_phones = set()
    orchestrator = Orchestrator([source])
    results = await orchestrator.buscar_fuente(
        source,
        ["q1", "q2", "q3", "q4"],
        "Bogotá, Cundinamarca, Colombia",
        {"ciudad": "Bogotá", "departamento": "Cundinamarca", "pais": "Colombia"},
        context=AsyncMock(),
        limit=2,
        cold_call_mode=True,
        known_phone_ids=set(),
        callable_phone_ids=callable_phones,
    )

    assert source.calls == ["q1", "q2", "q3"]
    assert len(callable_phones) == 2
    assert len(results) == 2
    with db.open_conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 2

    cleanup_test_db()

if __name__ == "__main__":
    asyncio.run(test_integration_flow())

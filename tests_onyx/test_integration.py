import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.orchestrator import Orchestrator
from sources.base_source import BaseSource, Lead
import db

# Mock DB
TEST_DB = "data/test_integration.db"
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

if __name__ == "__main__":
    asyncio.run(test_integration_flow())

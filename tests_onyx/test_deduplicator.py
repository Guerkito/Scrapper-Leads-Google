import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.deduplicator import Deduplicator
from sources.base_source import Lead

def test_deduplication():
    dedup = Deduplicator()
    
    leads = [
        # Match por nombre fuzzy + ciudad
        Lead(nombre="Onyx Software SAS", ciudad="Bogota", nicho="Tech", fuente="f1", telefono="111"),
        Lead(nombre="Onyx Software", ciudad="Bogota", nicho="Tech", fuente="f2", email="test@onyx.com"),
        
        # Match por teléfono
        Lead(nombre="Restaurante El Sabor", ciudad="Cali", nicho="Comida", fuente="f1", telefono="222"),
        Lead(nombre="Sabor Valluno", ciudad="Cali", nicho="Comida", fuente="f2", telefono="222"),
        
        # Match por NIT
        Lead(nombre="Empresa A", ciudad="Medellin", nicho="X", fuente="f1", nit="12345"),
        Lead(nombre="Diferente Nombre Pero Mismo NIT", ciudad="Medellin", nicho="Y", fuente="f2", nit="12345"),
        
        # No es duplicado (distinta ciudad)
        Lead(nombre="Tienda X", ciudad="Pasto", nicho="Retail", fuente="f1", telefono="333"),
        Lead(nombre="Tienda X", ciudad="Neiva", nicho="Retail", fuente="f2", telefono="444")
    ]
    
    unicos = dedup.deduplicar(leads)
    
    # 8 leads originales -> Deberían quedar 5
    # 1. Onyx Software (2 merged)
    # 2. Restaurante/Sabor (2 merged por tel)
    # 3. Empresa A (2 merged por NIT)
    # 4. Tienda X Pasto
    # 5. Tienda X Neiva
    
    print(f"Total únicos: {len(unicos)}")
    for l in unicos:
        print(f"- {l.nombre} ({l.ciudad}) | Tel: {l.telefono} | NIT: {l.nit}")

    assert len(unicos) == 5
    
    # Verificar merge de datos
    onyx = next(l for l in unicos if "Onyx" in l.nombre)
    assert onyx.telefono == "111"
    assert onyx.email == "test@onyx.com"
    assert len(onyx.fuentes_encontrado) == 2

    print("✅ Unit Test (Deduplicación) PASSED")

if __name__ == "__main__":
    try:
        test_deduplication()
    except Exception as e:
        print(f"❌ Unit Test (Deduplicación) FAILED: {e}")
        import traceback
        traceback.print_exc()

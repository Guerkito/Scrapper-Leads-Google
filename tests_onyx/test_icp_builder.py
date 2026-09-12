import json

import pytest

from engine import icp_builder
from services import product_campaigns as pc


def test_parse_icp_accepts_fenced_json_and_normalizes():
    raw = """```json
    {
      "negocio": "Software de turnos para clínicas",
      "pitch": "Menos espera, más citas atendidas",
      "roles_decision": ["Gerencia", "Dirección médica"],
      "dolores": ["filas", "ausencias"],
      "segmentos": [
        {"label": "Clínicas dentales", "queries": ["odontólogo", "clínica dental"]},
        {"label": "Centros médicos", "queries": ["centro médico", "IPS"]}
      ]
    }
    ```"""

    icp = icp_builder.parse_icp(raw)

    assert icp["negocio"].startswith("Software")
    assert icp["segmentos"][1]["queries"] == ["centro médico", "IPS"]
    assert icp["roles_decision"] == ["Gerencia", "Dirección médica"]


def test_parse_icp_rejects_missing_segments():
    with pytest.raises(ValueError):
        icp_builder.parse_icp(
            json.dumps({"negocio": "x", "pitch": "y", "segmentos": []})
        )


def test_register_custom_campaign_is_searchable_and_persisted(tmp_path, monkeypatch):
    path = tmp_path / "custom_campaigns.json"
    monkeypatch.setattr(pc, "CUSTOM_CAMPAIGNS_PATH", str(path))

    key = pc.register_custom_campaign({
        "negocio": "Turnos para clínicas",
        "pitch": "Menos espera",
        "roles_decision": ["Gerencia"],
        "segmentos": [
            {"label": "Clínicas dentales", "queries": ["odontólogo", "clínica dental"]},
        ],
    })
    try:
        assert key in pc.campaign_options()
        assert pc.build_search_terms(key, pc.default_segments(key)) == [
            "odontólogo", "clínica dental"
        ]
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved[key]["pitch"] == "Menos espera"
    finally:
        pc.PRODUCT_CAMPAIGNS.pop(key, None)

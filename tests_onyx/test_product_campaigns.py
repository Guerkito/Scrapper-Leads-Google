import db
from services.product_campaigns import (
    apply_campaign_context,
    build_search_terms,
    campaign_label,
    campaign_options,
    default_segments,
    get_campaign,
    score_campaign_lead,
    segment_for_query,
)
from sources.base_source import Lead


def _fresh_db(tmp_path):
    db.DB_PATH = str(tmp_path / "product_campaigns.db")
    db.init_db()
    return db.open_conn()


def test_campaign_segments_control_search_terms():
    public_terms = build_search_terms("watson_clinic", ["ese_publicas"])

    assert "ESE hospital" in public_terms
    assert "clínica médica" not in public_terms
    assert segment_for_query(
        "watson_clinic", "hospital municipal", ["ese_publicas"]
    ) == "ese_publicas"


def test_campaign_context_generates_product_fit_and_pitch():
    lead = Lead(
        "Clínica Central", "Bogotá", "clínica médica", "google_maps",
        pais="Colombia", telefono="6015550000", rating=4.5, reseñas=120,
    )

    apply_campaign_context(
        lead, "watson_auditor_ips", ["ips_privadas"], "clínica médica"
    )

    assert lead.campaign_label == campaign_label("watson_auditor_ips")
    assert lead.target_segment == "IPS y clínicas privadas"
    assert lead.fit_score >= 80
    assert "glosas" in lead.pitch_sugerido
    assert "Facturación" in lead.decision_roles


def test_full_onyx_portfolio_is_available_as_targeted_campaigns():
    expected = {
        "onyx_web",
        "onyx_ecommerce",
        "onyx_automation",
        "onyx_ai_integrations",
        "onyx_custom_software",
    }

    assert expected <= set(campaign_options())
    assert campaign_label("onyx_web") == "ONYX · Páginas web"
    assert "hojas de cálculo" in get_campaign("onyx_custom_software")["qualification_note"]


def test_onyx_campaigns_start_with_a_focused_segment_for_speed():
    assert default_segments("onyx_web") == ["servicios_profesionales"]
    assert build_search_terms("onyx_automation", default_segments("onyx_automation")) == [
        "empresa de logística", "empresa de transporte", "fábrica", "distribuidora"
    ]
    assert build_search_terms("onyx_automation", []) == []


def test_web_campaign_prioritizes_missing_website_without_inventing_a_need():
    without_site = Lead(
        "Odontología Central", "Bogotá", "odontólogo", "google_maps",
        telefono="6015550000", rating=4.6, reseñas=45,
    )
    with_site = Lead(
        "Odontología Norte", "Bogotá", "odontólogo", "google_maps",
        telefono="6015550001", sitio_web="https://example.com", rating=4.6, reseñas=45,
    )

    no_site_score, no_site_reason = score_campaign_lead(without_site, "onyx_web")
    site_score, _ = score_campaign_lead(with_site, "onyx_web")

    assert no_site_score > site_score
    assert "no se capturó sitio web" in no_site_reason


def test_custom_software_context_targets_the_right_decisor_and_pitch():
    lead = Lead(
        "Logística Andina", "Bogotá", "empresa de logística", "linkedin",
        email="gerencia@example.com", sitio_web="https://example.com",
    )

    apply_campaign_context(
        lead, "onyx_custom_software", ["operacion_compleja"], "empresa de logística"
    )

    assert lead.target_segment == "Operación compleja"
    assert "sistema hecho" in lead.pitch_sugerido
    assert "Gerencia general" in lead.decision_roles
    assert "estructura empresarial" in lead.fit_reason


def test_same_lead_keeps_multiple_product_opportunities(tmp_path):
    conn = _fresh_db(tmp_path)
    first = Lead(
        "IPS Central", "Bogotá", "IPS", "google_maps", pais="Colombia",
        maps_url="https://maps.google.com/!1s0xabc:0xdef", telefono="6015550000",
    )
    apply_campaign_context(first, "watson_clinic", ["ips_privadas"], "IPS")
    assert db.save_lead(first, conn) == 1

    second = Lead(
        "IPS Central", "Bogotá", "IPS", "google_maps", pais="Colombia",
        maps_url="https://maps.google.com/!1s0xabc:0xdef", telefono="6015550000",
    )
    apply_campaign_context(
        second, "watson_auditor_ips", ["ips_privadas"], "IPS de salud"
    )
    assert db.save_lead(second, conn) == 0
    conn.commit()

    assert conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 1
    opportunities = conn.execute(
        "SELECT product_key FROM lead_opportunities ORDER BY product_key"
    ).fetchall()
    assert [row[0] for row in opportunities] == [
        "watson_auditor_ips", "watson_clinic"
    ]
    conn.close()


def test_campaign_columns_exist_for_history_and_favorites(tmp_path):
    conn = _fresh_db(tmp_path)
    history_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(search_history)")
    }
    favorite_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(search_favorites)")
    }
    conn.close()

    assert {"product_campaign", "target_segments"} <= history_columns
    assert {"product_campaign", "target_segments"} <= favorite_columns

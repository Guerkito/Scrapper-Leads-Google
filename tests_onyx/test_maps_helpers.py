import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.maps_helpers import (
    _claim_place_for_scrape,
    _extract_phone_candidate,
    _extract_place_coordinates,
    _names_match,
    _norm_name,
    _parse_rating,
    _parse_review_count,
    click_cookie_consent,
)
from sources.google_maps import _panel_element


def test_norm_name_matching():
    assert _norm_name("  Café—Central ") == "cafe central"
    assert _names_match("Café Central", "CAFE CENTRAL")
    assert _names_match("Café Central · Restaurante", "Café Central")
    assert not _names_match("Café Central", "Café Central Norte")
    assert not _names_match("Joyería Luna", "Joyería Sol")


def test_place_coords_priority():
    # Las coords del negocio (!3d!4d) deben ganar sobre el centro del mapa (@)
    url = "https://google.com/maps/place/X/@4.60,-74.08,14z/data=!3d4.6533!4d-74.0621"
    assert _extract_place_coordinates(url) == (4.6533, -74.0621)


def test_map_center_is_not_used_as_place_coordinates():
    url = "https://google.com/maps/place/X/@4.60,-74.08,14z"
    assert _extract_place_coordinates(url) == (None, None)


def test_cookie_consent_uses_one_total_timeout():
    class FakeLocator:
        def __init__(self):
            self.first = self
            self.calls = []

        async def click(self, **kwargs):
            self.calls.append(kwargs)
            raise TimeoutError("banner ausente")

    class FakePage:
        def __init__(self):
            self.locator_obj = FakeLocator()
            self.selectors = []

        def locator(self, selector):
            self.selectors.append(selector)
            return self.locator_obj

    page = FakePage()
    assert asyncio.run(click_cookie_consent(page, timeout=750)) is False
    assert len(page.selectors) == 1
    assert page.locator_obj.calls == [{"timeout": 750, "no_wait_after": True}]


def test_maps_value_parsers_cover_localized_formats():
    assert _parse_rating("4,7 estrellas") == 4.7
    assert _parse_rating("Rated 4.5 out of 5") == 4.5
    assert _parse_review_count("1.234 reseñas") == 1234
    assert _parse_review_count("1,2 mil reseñas") == 1200
    assert _parse_review_count("2.5K reviews") == 2500
    assert _extract_phone_candidate("phone:tel:+57 300 123 4567") == "+57 300 123 4567"


def test_claim_place_skips_database_and_in_mission_duplicates():
    known = {"0x1:0x2"}
    seen = set()
    known_url = "https://maps.google.com/data=!1s0x1:0x2!3d4.6!4d-74.1"
    new_url = "https://maps.google.com/data=!1s0x3:0x4!3d4.7!4d-74.2"
    assert _claim_place_for_scrape(known_url, known, seen) is False
    assert _claim_place_for_scrape(new_url, known, seen) is True
    assert _claim_place_for_scrape(new_url, known, seen) is False
    assert seen == {"0x3:0x4"}


def test_panel_element_never_falls_back_to_search_feed():
    class FakePanel:
        async def query_selector(self, selector):
            return None

    class FakePage:
        async def query_selector(self, selector):
            raise AssertionError("no debe leer el listado cuando existe el panel")

    assert asyncio.run(_panel_element(FakePage(), FakePanel(), "span.MW4etd")) is None
    assert asyncio.run(_panel_element(FakePage(), None, "span.MW4etd")) is None


if __name__ == "__main__":
    test_norm_name_matching()
    test_place_coords_priority()
    print("OK")

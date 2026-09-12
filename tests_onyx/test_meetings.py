import db
from services import meetings


def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "meetings.db"))
    db.init_db()


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_booking_fields_extracts_start_and_link():
    start, url = meetings.booking_fields({
        "start": "2026-09-20T15:30:00.000Z",
        "meetingUrl": "https://meet.google.com/abc-defg",
    })
    assert start == "2026-09-20 15:30"
    assert url == "https://meet.google.com/abc-defg"

    start, url = meetings.booking_fields({"start": "", "location": "Oficina 3"})
    assert start == "" and url == ""


def test_fetch_upcoming_parses_calcom_payload(monkeypatch):
    monkeypatch.setattr(meetings, "CALCOM_API_KEY", "cal_test")
    monkeypatch.setattr(
        meetings.requests, "get",
        lambda *args, **kwargs: _FakeResponse({
            "status": "success",
            "data": [{"start": "2026-09-20T15:30:00Z", "status": "accepted"}],
        }),
    )

    booking = meetings.fetch_upcoming("ana@example.com")

    assert booking["start"].startswith("2026-09-20")


def test_fetch_upcoming_tolerates_empty_data(monkeypatch):
    monkeypatch.setattr(meetings, "CALCOM_API_KEY", "cal_test")
    monkeypatch.setattr(
        meetings.requests, "get",
        lambda *args, **kwargs: _FakeResponse({"status": "success", "data": []}),
    )

    assert meetings.fetch_upcoming("ana@example.com") is None


def test_sync_meetings_confirms_and_reverts(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    monkeypatch.setattr(meetings, "CALCOM_API_KEY", "cal_test")
    with db.open_conn() as conn:
        conn.execute(
            "INSERT INTO leads (nombre, email, estado) VALUES ('Ana', 'ana@x.com', 'Interesado')"
        )
        conn.execute(
            "INSERT INTO leads (nombre, email, estado, reunion_at) "
            "VALUES ('Beto', 'beto@x.com', 'Reunión', '2026-09-01 10:00')"
        )

    responses = {
        "ana@x.com": {"start": "2026-09-20T15:30:00.000Z", "meetingUrl": "https://meet/x"},
        "beto@x.com": None,
    }
    monkeypatch.setattr(meetings, "fetch_upcoming", lambda email: responses[email])

    result = meetings.sync_meetings()

    assert result["confirmed"] == 1
    assert result["reverted"] == 1
    with db.open_conn() as conn:
        ana = conn.execute(
            "SELECT estado, reunion_at, reunion_url FROM leads WHERE nombre = 'Ana'"
        ).fetchone()
        beto = conn.execute(
            "SELECT estado, reunion_at FROM leads WHERE nombre = 'Beto'"
        ).fetchone()
    assert ana == ("Reunión", "2026-09-20 15:30", "https://meet/x")
    assert beto == ("Interesado", None)


def test_sync_meetings_skips_without_key(monkeypatch):
    monkeypatch.setattr(meetings, "CALCOM_API_KEY", "")
    result = meetings.sync_meetings()
    assert result["skipped"] is True

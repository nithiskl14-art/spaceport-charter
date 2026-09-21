from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app

CENTRAL = ZoneInfo("America/Chicago")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    with TestClient(app) as test_client:
        yield test_client


def future_day() -> str:
    return (datetime.now(CENTRAL) + timedelta(days=30)).date().isoformat()


def booking(ship=1, start="09:00", end="10:00", day=None):
    day = day or future_day()

    def stamp(clock):
        return datetime.fromisoformat(f"{day}T{clock}:00").replace(tzinfo=CENTRAL).isoformat()
    return {"shipId": ship, "pilotName": "Test Pilot", "startTime": stamp(start), "endTime": stamp(end)}


def test_create_booking_and_list(client):
    response = client.post("/api/bookings", json=booking())
    assert response.status_code == 201
    assert response.json()["shipName"] == "USS Wanderer"
    day = future_day()
    assert len(client.get(f"/api/bookings?startDate={day}&endDate={day}").json()) == 1


def test_booking_summary_avoids_downloading_history(client):
    empty = client.get("/api/bookings/summary")
    assert empty.status_code == 200
    assert empty.json()["totalRecords"] == 0
    assert empty.json()["latestBookingDate"] is None

    assert client.post("/api/bookings", json=booking()).status_code == 201
    summary = client.get("/api/bookings/summary")
    assert summary.status_code == 200
    assert summary.json() == {
        "totalRecords": 1,
        "latestBookingDate": future_day(),
        "todayCount": 0,
    }


@pytest.mark.parametrize("start,end", [("09:30", "10:30"), ("10:15", "11:00"), ("08:30", "09:00")])
def test_rejects_overlap_and_insufficient_buffer(client, start, end):
    assert client.post("/api/bookings", json=booking()).status_code == 201
    assert client.post("/api/bookings", json=booking(start=start, end=end)).status_code == 409


def test_returns_specific_overlap_message(client):
    client.post("/api/bookings", json=booking())
    response = client.post("/api/bookings", json=booking(start="09:30", end="10:30"))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "BOOKING_OVERLAP"
    assert response.json()["detail"]["message"] == "This time overlaps an existing booking for this ship."


def test_returns_specific_refueling_message(client):
    client.post("/api/bookings", json=booking())
    response = client.post("/api/bookings", json=booking(start="10:15", end="11:00"))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "REFUEL_BUFFER_REQUIRED"
    assert response.json()["detail"]["message"] == "A 30-minute refueling period is required between bookings."


def test_accepts_exact_thirty_minute_buffer(client):
    assert client.post("/api/bookings", json=booking()).status_code == 201
    assert client.post("/api/bookings", json=booking(start="10:30", end="11:30")).status_code == 201


def test_allows_same_time_for_different_ships(client):
    assert client.post("/api/bookings", json=booking()).status_code == 201
    assert client.post("/api/bookings", json=booking(ship=2)).status_code == 201


@pytest.mark.parametrize("start,end", [("05:30", "07:00"), ("21:30", "22:30")])
def test_rejects_outside_operating_hours(client, start, end):
    response = client.post("/api/bookings", json=booking(start=start, end=end))
    assert response.status_code == 422


def test_accepts_operating_hour_boundaries(client):
    assert client.post("/api/bookings", json=booking(start="06:00", end="22:00")).status_code == 201


def test_unavailable_endpoint_returns_buffered_period(client):
    client.post("/api/bookings", json=booking())
    response = client.get(f"/api/ships/1/unavailable?date={future_day()}")
    assert response.status_code == 200
    period = response.json()["unavailable"][0]
    assert response.json()["refuelBufferMinutes"] == 30
    assert datetime.fromisoformat(period["startTime"]).astimezone(CENTRAL).strftime("%H:%M") == "09:00"
    assert datetime.fromisoformat(period["endTime"]).astimezone(CENTRAL).strftime("%H:%M") == "10:30"


def test_unavailable_endpoint_merges_adjacent_periods(client):
    assert client.post("/api/bookings", json=booking(start="09:00", end="10:00")).status_code == 201
    assert client.post("/api/bookings", json=booking(start="10:30", end="11:30")).status_code == 201

    response = client.get(f"/api/ships/1/unavailable?date={future_day()}")
    assert response.status_code == 200
    periods = response.json()["unavailable"]
    assert len(periods) == 1
    assert datetime.fromisoformat(periods[0]["startTime"]).astimezone(CENTRAL).strftime("%H:%M") == "09:00"
    assert datetime.fromisoformat(periods[0]["endTime"]).astimezone(CENTRAL).strftime("%H:%M") == "12:00"


def test_booking_before_existing_one_still_requires_refueling_buffer(client):
    client.post("/api/bookings", json=booking(start="09:00", end="10:00"))
    response = client.post("/api/bookings", json=booking(start="07:30", end="08:45"))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "REFUEL_BUFFER_REQUIRED"


def test_rejects_unknown_ship_and_naive_timestamp(client):
    assert client.post("/api/bookings", json=booking(ship=99)).status_code == 404
    payload = booking()
    payload["startTime"] = "2026-10-15T09:00:00"
    assert client.post("/api/bookings", json=payload).status_code == 422


def test_rejects_booking_in_the_past(client):
    yesterday = (datetime.now(CENTRAL) - timedelta(days=1)).date().isoformat()
    response = client.post("/api/bookings", json=booking(day=yesterday))
    assert response.status_code == 422
    assert response.json()["detail"] == "Booking start time must be in the future"


def test_concurrent_conflicting_requests_create_only_one_booking(client):
    ready = Barrier(2)

    def submit():
        ready.wait()
        return client.post("/api/bookings", json=booking()).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(lambda _: submit(), range(2)))

    assert statuses == [201, 409]
    day = future_day()
    stored = client.get(f"/api/bookings?startDate={day}&endDate={day}").json()
    assert len(stored) == 1


def test_health_check_and_security_headers(client):
    response = client.get("/api/health", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
    assert response.headers["X-Request-ID"] == "test-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_read_connection_scope_closes_connection(client):
    with database.connection_scope() as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1

    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")

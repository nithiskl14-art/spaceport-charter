from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .config import (
    CENTRAL_TIMEZONE,
    OPERATING_END_HOUR,
    OPERATING_START_HOUR,
    REFUEL_BUFFER_MINUTES,
)
from .database import connection_scope, transaction
from .schemas import BookingCreate

CENTRAL = ZoneInfo(CENTRAL_TIMEZONE)
BUFFER = timedelta(minutes=REFUEL_BUFFER_MINUTES)


def utc_string(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def operating_window(day: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, time(OPERATING_START_HOUR), CENTRAL),
        datetime.combine(day, time(OPERATING_END_HOUR), CENTRAL),
    )


def serialize_booking(row) -> dict:
    return {
        "id": row["id"],
        "shipId": row["ship_id"],
        "shipName": row["ship_name"],
        "pilotName": row["pilot_name"],
        "startTime": row["start_time"],
        "endTime": row["end_time"],
    }


def validate_booking_times(payload: BookingCreate) -> tuple[datetime, datetime]:
    start = payload.startTime.astimezone(CENTRAL)
    end = payload.endTime.astimezone(CENTRAL)
    if start >= end:
        raise HTTPException(422, "End time must be after start time")
    if start <= datetime.now(CENTRAL):
        raise HTTPException(422, "Booking start time must be in the future")
    if start.date() != end.date():
        raise HTTPException(422, "A booking must start and end on the same Central Time date")
    opens, closes = operating_window(start.date())
    if start < opens or end > closes:
        raise HTTPException(422, "Bookings must be entirely between 6:00 AM and 10:00 PM Central Time")
    return start, end


def create_booking(payload: BookingCreate) -> dict:
    start, end = validate_booking_times(payload)
    start_utc, end_utc = utc_string(start), utc_string(end)
    buffered_start = utc_string(start - BUFFER)
    buffered_end = utc_string(end + BUFFER)

    with transaction() as connection:
        ship = connection.execute("SELECT id FROM ships WHERE id = ?", (payload.shipId,)).fetchone()
        if ship is None:
            raise HTTPException(404, "Ship not found")

        overlap = connection.execute(
            """
            SELECT b.*, s.name AS ship_name
            FROM bookings b JOIN ships s ON s.id = b.ship_id
            WHERE b.ship_id = ?
              AND b.start_time < ?
              AND b.end_time > ?
            ORDER BY b.start_time LIMIT 1
            """,
            (payload.shipId, end_utc, start_utc),
        ).fetchone()
        if overlap:
            raise HTTPException(
                409,
                {
                    "code": "BOOKING_OVERLAP",
                    "message": "This time overlaps an existing booking for this ship.",
                    "conflictStart": overlap["start_time"],
                    "conflictEnd": overlap["end_time"],
                },
            )

        buffer_conflict = connection.execute(
            """
            SELECT b.*, s.name AS ship_name
            FROM bookings b JOIN ships s ON s.id = b.ship_id
            WHERE b.ship_id = ?
              AND b.start_time < ?
              AND b.end_time > ?
            ORDER BY b.start_time LIMIT 1
            """,
            (payload.shipId, buffered_end, buffered_start),
        ).fetchone()
        if buffer_conflict:
            raise HTTPException(
                409,
                {
                    "code": "REFUEL_BUFFER_REQUIRED",
                    "message": "A 30-minute refueling period is required between bookings.",
                    "conflictStart": buffer_conflict["start_time"],
                    "conflictEnd": buffer_conflict["end_time"],
                },
            )

        cursor = connection.execute(
            "INSERT INTO bookings(ship_id, pilot_name, start_time, end_time) VALUES (?, ?, ?, ?)",
            (payload.shipId, payload.pilotName, start_utc, end_utc),
        )
        row = connection.execute(
            """
            SELECT b.*, s.name AS ship_name FROM bookings b
            JOIN ships s ON s.id = b.ship_id WHERE b.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return serialize_booking(row)


def get_unavailable(ship_id: int, day: date) -> dict:
    opens, closes = operating_window(day)
    query_start = utc_string(opens)
    query_end = utc_string(closes)
    with connection_scope() as connection:
        if connection.execute("SELECT 1 FROM ships WHERE id = ?", (ship_id,)).fetchone() is None:
            raise HTTPException(404, "Ship not found")
        rows = connection.execute(
            """
            SELECT start_time, end_time FROM bookings
            WHERE ship_id = ? AND start_time < ? AND end_time > ?
            ORDER BY start_time
            """,
            (ship_id, query_end, query_start),
        ).fetchall()

    periods: list[tuple[datetime, datetime]] = []
    for row in rows:
        # The displayed unavailable period is the booking itself followed by
        # the required refueling time. The backend booking validator separately
        # checks that a booking placed before this one leaves the same 30 minutes.
        start = max(datetime.fromisoformat(row["start_time"]).astimezone(CENTRAL), opens)
        end = min(datetime.fromisoformat(row["end_time"]).astimezone(CENTRAL) + BUFFER, closes)
        if start < end:
            if periods and start <= periods[-1][1]:
                periods[-1] = (periods[-1][0], max(periods[-1][1], end))
            else:
                periods.append((start, end))

    return {
        "shipId": ship_id,
        "date": day,
        "timezone": CENTRAL_TIMEZONE,
        "operatingStart": opens,
        "operatingEnd": closes,
        "refuelBufferMinutes": REFUEL_BUFFER_MINUTES,
        "unavailable": [{"startTime": start, "endTime": end} for start, end in periods],
    }

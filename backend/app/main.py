from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta
import logging
from pathlib import Path
import sqlite3
import time as clock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import CORS_ORIGINS
from .database import connection_scope, initialize_database
from .schemas import Booking, BookingCreate, BookingSummary, Ship, UnavailableResponse
from .services import CENTRAL, create_booking, get_unavailable, serialize_booking, utc_string


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("spaceport.api")

app = FastAPI(title="Spaceport Charter API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = clock.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (clock.perf_counter() - started) * 1000,
    )
    return response


@app.exception_handler(sqlite3.OperationalError)
async def database_unavailable(request: Request, error: sqlite3.OperationalError):
    logger.exception("Database operation failed for %s", request.url.path, exc_info=error)
    return JSONResponse(
        status_code=503,
        content={"detail": "The booking database is temporarily unavailable. Please retry."},
        headers={"Retry-After": "1"},
    )


@app.get("/api/health")
def health():
    with connection_scope() as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "ok", "database": "reachable"}


@app.get("/api/ships", response_model=list[Ship])
def list_ships():
    with connection_scope() as connection:
        return [dict(row) for row in connection.execute("SELECT id, name FROM ships ORDER BY id")]


@app.get("/api/ships/{ship_id}/unavailable", response_model=UnavailableResponse)
def unavailable(ship_id: int, date: date = Query(...)):
    return get_unavailable(ship_id, date)


@app.post("/api/bookings", response_model=Booking, status_code=201)
def add_booking(payload: BookingCreate):
    return create_booking(payload)


@app.get("/api/bookings/summary", response_model=BookingSummary)
def booking_summary():
    today = datetime.now(CENTRAL).date()
    today_start = utc_string(datetime.combine(today, time.min, CENTRAL))
    tomorrow_start = utc_string(
        datetime.combine(today + timedelta(days=1), time.min, CENTRAL)
    )
    with connection_scope() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_records,
                MAX(start_time) AS latest_start,
                SUM(CASE WHEN start_time >= ? AND start_time < ? THEN 1 ELSE 0 END)
                    AS today_count
            FROM bookings
            """,
            (today_start, tomorrow_start),
        ).fetchone()

    latest_date = None
    if row["latest_start"]:
        latest_date = (
            datetime.fromisoformat(row["latest_start"]).astimezone(CENTRAL).date()
        )
    return {
        "totalRecords": row["total_records"],
        "latestBookingDate": latest_date,
        "todayCount": row["today_count"] or 0,
    }


@app.get("/api/bookings", response_model=list[Booking])
def list_bookings(startDate: date | None = None, endDate: date | None = None):
    if startDate and endDate and startDate > endDate:
        raise HTTPException(422, "startDate cannot be after endDate")
    clauses, params = [], []
    if startDate:
        clauses.append("b.end_time > ?")
        params.append(utc_string(datetime.combine(startDate, time.min, CENTRAL)))
    if endDate:
        clauses.append("b.start_time < ?")
        params.append(utc_string(datetime.combine(endDate + timedelta(days=1), time.min, CENTRAL)))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection_scope() as connection:
        rows = connection.execute(
            f"""SELECT b.*, s.name AS ship_name FROM bookings b
            JOIN ships s ON s.id = b.ship_id {where}
            ORDER BY s.id, b.start_time""",
            params,
        ).fetchall()
    return [serialize_booking(row) for row in rows]


frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend.exists():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = frontend / path
        return FileResponse(candidate if candidate.is_file() else frontend / "index.html")

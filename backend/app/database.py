import sqlite3
from contextlib import contextmanager

from .config import DATABASE_PATH, SQLITE_TIMEOUT_SECONDS

DEFAULT_SHIPS = [
    (1, "USS Wanderer"),
    (2, "Nostromo"),
    (3, "Serenity"),
    (4, "Rocinante"),
    (5, "Millennium Falcon"),
]


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=SQLITE_TIMEOUT_SECONDS,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(f"PRAGMA busy_timeout = {int(SQLITE_TIMEOUT_SECONDS * 1000)}")
    return connection


@contextmanager
def connection_scope():
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def transaction():
    connection = connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with connection_scope() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS ships (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_id INTEGER NOT NULL REFERENCES ships(id),
                pilot_name TEXT NOT NULL CHECK(length(trim(pilot_name)) > 0),
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK(start_time < end_time)
            );

            CREATE INDEX IF NOT EXISTS idx_bookings_ship_time
            ON bookings(ship_id, start_time, end_time);
            """
        )
        # A fresh installation must be usable before the optional historical
        # booking seed is imported. INSERT OR IGNORE preserves existing data.
        connection.executemany(
            "INSERT OR IGNORE INTO ships(id, name) VALUES (?, ?)", DEFAULT_SHIPS
        )
        connection.commit()

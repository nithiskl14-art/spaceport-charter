import argparse
import json
from pathlib import Path

from app.database import connection_scope, initialize_database
from app.services import utc_string
from datetime import datetime


def load(path: Path, reset: bool = False, if_empty: bool = False) -> None:
    data = json.loads(path.read_text())
    initialize_database()
    with connection_scope() as connection:
        if if_empty and connection.execute("SELECT 1 FROM bookings LIMIT 1").fetchone():
            print("Database already contains bookings; seed import skipped")
            return
        if reset:
            connection.execute("DELETE FROM bookings")
            connection.execute("DELETE FROM ships")
        connection.executemany(
            "INSERT OR REPLACE INTO ships(id, name) VALUES (:id, :name)", data["ships"]
        )
        connection.executemany(
            "INSERT INTO bookings(ship_id, pilot_name, start_time, end_time) VALUES (?, ?, ?, ?)",
            [
                (b["shipId"], b["pilotName"], utc_string(datetime.fromisoformat(b["startTime"])), utc_string(datetime.fromisoformat(b["endTime"])))
                for b in data["bookings"]
            ],
        )
        connection.commit()
    print(f"Loaded {len(data['ships'])} ships and {len(data['bookings'])} bookings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--if-empty", action="store_true")
    args = parser.parse_args()
    load(args.file, args.reset, args.if_empty)

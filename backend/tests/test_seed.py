import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from contextlib import closing


ROOT = Path(__file__).resolve().parents[2]


def test_generated_seed_imports_all_ships_and_bookings(tmp_path):
    seed_file = tmp_path / "seed.json"
    generated = subprocess.run(
        [sys.executable, str(ROOT / "seed.py")],
        check=True,
        capture_output=True,
        text=True,
    )
    seed_file.write_text(generated.stdout)

    payload = json.loads(generated.stdout)
    assert len(payload["ships"]) == 5
    assert len(payload["bookings"]) == 3000

    database = tmp_path / "seeded.db"
    environment = {**os.environ, "DATABASE_PATH": str(database)}
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "backend" / "seed.py"),
            str(seed_file),
            "--reset",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM ships").fetchone()[0] == 5
        assert connection.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 3000
        per_ship = connection.execute(
            "SELECT ship_id, COUNT(*) FROM bookings GROUP BY ship_id ORDER BY ship_id"
        ).fetchall()
    assert per_ship == [(1, 600), (2, 600), (3, 600), (4, 600), (5, 600)]

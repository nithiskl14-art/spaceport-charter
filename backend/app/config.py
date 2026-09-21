import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "spaceport.db"))
CENTRAL_TIMEZONE = "America/Chicago"
OPERATING_START_HOUR = 6
OPERATING_END_HOUR = 22
REFUEL_BUFFER_MINUTES = 30
SQLITE_TIMEOUT_SECONDS = float(os.getenv("SQLITE_TIMEOUT_SECONDS", "10"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

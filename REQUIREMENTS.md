# Requirement checklist

This file maps each assignment requirement to its implementation and verification.

| Requirement | Implementation | Verification |
|---|---|---|
| React frontend | `frontend/src/App.jsx` | `npm run build` |
| Python backend | FastAPI routes in `backend/app/main.py` | API tests |
| Persistent database | SQLite schema in `backend/app/database.py` | Persistence and API tests |
| Charter screen | `Charter` component | Manual booking flow |
| Fleet dashboard | Date-scoped `Fleet` component, grouped by ship | Summary, seeded timeline, and API tests |
| Pilot name | Validated request field and dashboard display | Creation test |
| No overlap | Transactional query in `create_booking` | Overlap and concurrent-request tests |
| 30-minute refueling | Transactional buffer query | Before/after boundary tests |
| 6 AM–10 PM Central | `operating_window` using `America/Chicago` | Boundary tests |
| Backend unavailability | `GET /api/ships/{id}/unavailable`; UI disables conflicts from this response | Endpoint and frontend availability tests |
| Minimum data model | `ships` and `bookings` tables | Schema initialization |
| Supplied seed command | `python seed.py > seed.json` | Full 5-ship / 3,000-booking import test |
| No authentication | Deliberately omitted as requested | Scope documented in README |

## Deliberate scope

The UI uses 30-minute choices, but the requirements do not impose a maximum
charter duration. Editing, cancellation, and authentication are not included.
SQLite keeps the submission easy to run; a multi-instance production service
would move conflict protection to PostgreSQL constraints or advisory locks.

## Operational safeguards

- Database-aware health endpoint and container health check
- Request IDs, access logs, and browser security headers
- Configurable CORS origins and SQLite writer timeout
- Deterministic connection closure for all database operations
- DST-transition coverage for Central Time conversion
- Non-root production container
- Pinned frontend and backend dependencies
- CI coverage for backend versions, frontend tests, and production build

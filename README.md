# VitalWatch API

Asynchronous FastAPI backend for the medical vitals monitoring application.

## Setup Instructions

1. `cp .env.example .env` → fill in your Postgres creds
2. `createdb vitalwatch`
3. `alembic upgrade head`
4. `python seed.py`
5. `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
6. Open http://localhost:8000/docs
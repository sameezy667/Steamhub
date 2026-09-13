# Testing Guide — Steamhub

Comprehensive instructions for running unit, integration, and end-to-end tests for the Steamhub application.

---

## 1. Prerequisites

Ensure dependencies are installed for both backend and frontend environments:

### Backend Python Environment
```bash
cd backend
# Using active virtual environment:
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend Environment
```bash
cd frontend
npm install
```

---

## 2. Running Backend Automated Tests

All backend tests use **Pytest** with `pytest-asyncio` in auto-async mode. Tests execute against an isolated SQLite async test database (configured in `backend/tests/conftest.py`) and mock external Steam API calls.

### Run All Backend Tests
From the project root:
```bash
backend/.venv/bin/pytest backend/tests
```
*Or, if the virtual environment is activated:*
```bash
pytest backend/tests
```

### Run Tests with Verbose Output
```bash
pytest backend/tests -v
```

### Run Specific Test Modules
```bash
# 1. API routes, rate limiting, and heatmap aggregations
pytest backend/tests/test_api.py -v

# 2. Steam OpenID 2.0 authentication, nonce CSRF verification
pytest backend/tests/test_auth.py -v

# 3. Snapshot diffing, monotonicity, and advisory locking
pytest backend/tests/test_poller.py -v

# 4. Backfill engine and aggregate parity
pytest backend/tests/test_backfill.py -v

# 5. UTC date utilities & truncation
pytest backend/tests/test_utils.py -v
```

### Test Coverage Breakdown
| Test File | Scope / Assertions |
|---|---|
| `test_api.py` | Heatmap pre-aggregated queries, user game lists, profile status, auth protection, health checks |
| `test_auth.py` | OpenID login redirection, state token generation & verification, tampering rejection, session cookie validation |
| `test_poller.py` | Poller snapshot ingestion, playtime delta calculation, private profile skipping, advisory lock concurrency |
| `test_backfill.py` | Snapshot-to-daily_delta rollup consistency & parity verification |
| `test_utils.py` | Canonical UTC date truncation and hash generation consistency |

---

## 3. Frontend Validation & Production Build

Verify TypeScript types and Vite build integrity:

### Typecheck & Build
```bash
cd frontend
npm run build
```

### Development Server Preview
To launch the frontend locally with hot-reloading:
```bash
cd frontend
npm run dev
```

---

## 4. Manual End-to-End Integration Testing

To test the live stack with PostgreSQL and Steam Web API:

### Step 1: Start PostgreSQL Database
```bash
docker compose up -d
```

### Step 2: Configure Environment Variables
Create `backend/.env` based on `backend/.env.example`:
```bash
cp backend/.env.example backend/.env
```
Ensure your `STEAM_API_KEY` is provided in `backend/.env`.

### Step 3: Run Database Migrations
```bash
cd backend
alembic upgrade head
```

### Step 4: Start Backend API & Poller Scheduler
```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

### Step 5: Start Frontend
```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` to test the Steam OpenID login flow, heatmap rendering, and manual polling trigger.

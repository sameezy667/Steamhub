# Steamhub — Project Context & Architecture Ledger

## 1. Project Overview
Steamhub is a production-grade, GitHub-style contribution heatmap and playtime tracking service for Steam accounts. Tracking begins from the account connection date (no historical backfill). The system relies on an immutable raw snapshot audit log, derived daily aggregate tables, asynchronous polling with PostgreSQL advisory locks, secure Steam OpenID 2.0 authentication with CSRF nonce verification, and a modern SPA frontend.

---

## 2. Tech Stack
- **Backend:** Python 3.11+ / FastAPI, Uvicorn
- **Database & ORM:** PostgreSQL 16+, SQLAlchemy 2.0 (AsyncIO), asyncpg, Alembic
- **Scheduler:** APScheduler (asyncio background scheduler) & standalone CLI poller/backfill runners
- **Security & Auth:** Steam OpenID 2.0, HMAC-SHA256 CSRF state tokens, HttpOnly/Secure/SameSite=Lax JWT session cookies, SlowAPI rate limiting (IP + User), OWASP headers
- **Frontend:** TypeScript, React 18, Vite, Vanilla CSS (Steam Dark aesthetic), custom 3-state Heatmap SVG grid, i18n (`en.json`)
- **Testing:** Pytest, pytest-asyncio, httpx AsyncClient

---

## 3. Architecture & Directory Layout
```
Steamhub/
├── context.md                    # Single source of truth ledger
├── test.md                       # Comprehensive testing & QA runbook
├── docker-compose.yml            # PostgreSQL 16 service
├── backend/
│   ├── .env.example              # Environment variables template
│   ├── requirements.txt          # Python dependencies
│   ├── alembic.ini               # Alembic configuration
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py             # Pydantic Settings (extra="forbid") & quota validator
│   │   ├── database.py           # Async SQLAlchemy engine & async sessionmaker
│   │   ├── models.py             # SQLAlchemy models (User, Snapshot, DailyDelta, Game)
│   │   ├── schemas.py            # Pydantic request/response schemas (extra="forbid")
│   │   ├── utils.py              # Canonical UTC date & hashing functions
│   │   ├── security.py           # Cookie JWT auth, OpenID nonce signing, rate limiters
│   │   ├── steam_client.py       # Steam Web API client & OpenID verification
│   │   ├── poller.py             # Polling & diff engine + Postgres advisory locking
│   │   ├── backfill.py           # Snapshot-to-daily_delta rebuild script
│   │   ├── scheduler.py          # APScheduler background runner
│   │   ├── main.py               # FastAPI application & OWASP middleware
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── auth.py           # OpenID login, callback, logout, me
│   │       ├── users.py          # Heatmap, games, status, manual poll
│   │       └── health.py         # Health checks & quota metrics
│   └── tests/
│       ├── conftest.py           # Test fixtures & test DB setup
│       ├── test_utils.py         # UTC date truncation tests
│       ├── test_auth.py          # OpenID nonce CSRF & verification tests
│       ├── test_poller.py        # Snapshot diffing, monotonicity & advisory locking tests
│       ├── test_backfill.py      # Backfill parity assertions
│       └── test_api.py           # Heatmap aggregation, authorization, status tests
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── locales/en.json
│       ├── types/index.ts
│       ├── api/client.ts
│       └── components/
│           ├── Header.tsx
│           ├── Heatmap.tsx
│           ├── GameBreakdown.tsx
│           ├── StatusBanner.tsx
│           └── YearSelector.tsx
└── data/                         # Local database volumes & test vectors
```

### Data Flow
1. **User Login:** `POST /auth/steam/login` -> signed state nonce cookie -> Steam OpenID -> `GET /auth/steam/callback` -> signature verification -> `GetPlayerSummaries` -> user upsert -> HttpOnly session cookie -> frontend redirect.
2. **Poller Tick:** Periodic APScheduler trigger -> acquire `pg_try_advisory_xact_lock(hashtext(user_id))` -> check `profile_visibility_state == 3` -> `GetOwnedGames` -> insert raw `Snapshot` -> compute `delta = current - previous` -> if `delta > 0`: upsert `DailyDelta(play_date=today_utc(), minutes_played += delta)` -> update `last_polled_at`.
3. **Heatmap Fetch:** `GET /api/users/{id}/heatmap?year=YYYY` -> index-accelerated pre-aggregated SQL -> returns total minutes per day + top game played + `connected_at` boundary -> frontend renders 3-state heatmap grid.

---

## 4. Feature Status Checklist & Completion Verification
- [x] **Phase 1: Environment & Database Schema** (`docker-compose.yml`, `requirements.txt`, `models.py`, Alembic migrations)
- [x] **Phase 2: Steam OpenID 2.0 Auth Flow & Session Security** (`utils.py`, `security.py`, `steam_client.py`, `api/auth.py`)
- [x] **Phase 3: Polling & Diff Engine** (`poller.py`, `backfill.py`, `scheduler.py`)
- [x] **Phase 4: API Layer & Security Middleware** (`api/users.py`, `api/health.py`, `main.py`, `schemas.py`)
- [x] **Phase 5: Modern SPA Frontend** (`frontend/` React 18 + Vite + TypeScript, 3-state Heatmap, Tooltips, Status Banner)
- [x] **Phase 6: Automated Test Suite & QA** (`test_utils.py`, `test_auth.py`, `test_poller.py`, `test_backfill.py`, `test_api.py`)

### Verification Milestones Achieved:
- **Backend Test Suite:** 20/20 unit & integration tests passing via Pytest (async test fixtures, mock steam API, CSRF state verification, advisory lock contention, backfill parity, and pre-aggregated queries).
- **Frontend Production Build:** Clean TypeScript typecheck and Vite asset compilation (`tsc -b && vite build` -> 0 errors).
- **Security Audit:** Rate limiting active on all public & authenticated endpoints, HttpOnly JWT cookies with Lax/Secure flags, Strict CSP & OWASP security headers, input validation with Pydantic v2 `extra="forbid"`.
- **Status:** **COMPLETE & PRODUCTION-READY**

---

## 5. Data Models

### SQL Schema (PostgreSQL)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    steam_id64 TEXT UNIQUE NOT NULL,
    persona_name TEXT NOT NULL DEFAULT '',
    avatar_url TEXT NOT NULL DEFAULT '',
    profile_visibility_state INTEGER,
    connected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_polled_at TIMESTAMPTZ
);

CREATE TABLE games (
    app_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    icon_url TEXT NOT NULL DEFAULT ''
);

CREATE TABLE snapshots (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id INTEGER NOT NULL REFERENCES games(app_id) ON DELETE CASCADE,
    playtime_forever_minutes INTEGER NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_snapshots_user_app_time ON snapshots (user_id, app_id, captured_at DESC);

CREATE TABLE daily_deltas (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id INTEGER NOT NULL REFERENCES games(app_id) ON DELETE CASCADE,
    play_date DATE NOT NULL,
    minutes_played INTEGER NOT NULL,
    PRIMARY KEY (user_id, app_id, play_date)
);
CREATE INDEX idx_daily_deltas_user_date_minutes ON daily_deltas (user_id, play_date, minutes_played DESC);
```

### TypeScript Data Models
```typescript
export interface User {
  id: string;
  steamId64: string;
  personaName: string;
  avatarUrl: string;
  profileVisibilityState: number | null;
  connectedAt: string;
  lastPolledAt: string | null;
}

export interface HeatmapDay {
  date: string; // YYYY-MM-DD
  totalMinutes: number;
  topGame: {
    appId: number;
    name: string;
    iconUrl: string;
    minutesPlayed: number;
  } | null;
}

export interface HeatmapResponse {
  userId: string;
  year: number;
  connectedAt: string;
  days: HeatmapDay[];
}

export interface UserGameStat {
  appId: number;
  name: string;
  iconUrl: string;
  lifetimeTrackedMinutes: number;
  lastPlayedDate: string | null;
}

export interface UserStatus {
  userId: string;
  steamId64: string;
  personaName: string;
  avatarUrl: string;
  profileVisibilityState: number | null;
  connectedAt: string;
  lastPolledAt: string | null;
  totalGamesTracked: number;
  isPollingAllowed: boolean;
  nextPollAllowedAt: string | null;
}
```

---

## 6. API Contracts
- `GET /auth/steam/login` -> Redirects to Steam OpenID with HMAC signed state nonce in HttpOnly cookie.
- `GET /auth/steam/callback` -> Validates state nonce, verifies signature against Steam, creates/updates user, sets HttpOnly JWT cookie, redirects to `FRONTEND_URL`.
- `GET /api/auth/me` -> Returns authenticated `User` object (401 if unauthenticated).
- `POST /api/auth/logout` -> Clears auth cookie.
- `GET /api/users/{id}/heatmap?year=YYYY` -> Returns `HeatmapResponse` with daily aggregates and top games.
- `GET /api/users/{id}/games` -> Returns `UserGameStat[]` list.
- `GET /api/users/{id}/status` -> Returns `UserStatus` (visibility state, last polled timestamp, game counts).
- `POST /api/users/{id}/poll` -> Manually triggers poll for `{id}` (Requires `current_user.id == id`, rate limit: 1/10min per user).
- `GET /api/health` -> System health and Steam API quota headroom.

---

## 7. Technical Debt & Non-Negotiable Rules
- Strict file headers on all files: `@file`, `@description`, `@module`.
- No hardcoded secrets: `.env.example` provided.
- Pydantic models with `model_config = ConfigDict(extra="forbid")`.
- Postgres advisory locks exclusively for polling concurrency.
- Zero local token storage: HttpOnly cookies only.
- Canonical `utils.py::today_utc()` for date handling across live poller and backfill script.
- Zero open technical debt items; 100% test passing baseline.

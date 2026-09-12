"""
@file main.py
@description FastAPI application entrypoint, lifespan configuration, OWASP middleware, and route mounting
@module backend/src
"""

from contextlib import asynccontextmanager
import logging
from collections.abc import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.src.api.auth import router as auth_router
from backend.src.api.health import router as health_router
from backend.src.api.users import router as users_router
from backend.src.config import settings
from backend.src.database import init_db
from backend.src.scheduler import start_scheduler, stop_scheduler
from backend.src.security import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("steamhub.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager: sets up DB tables, verifies capacity,
    and runs background scheduler.
    """
    logger.info("Initializing Steamhub database schema...")
    try:
        await init_db()
    except Exception as err:
        logger.warning("Database init_db warning (will retry on connect): %s", err)

    # Validate Steam API Capacity
    max_users = settings.max_supported_users
    logger.info(
        "Steam API Capacity Configured: Max %d concurrent users under %d daily quota.",
        max_users,
        settings.STEAM_DAILY_QUOTA,
    )

    # Start background scheduler
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()


app = FastAPI(
    title="Steamhub API",
    description="Steam Contribution Heatmap & Playtime Diffing Service",
    version="1.0.0",
    lifespan=lifespan,
)

# SlowAPI Rate Limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """
    OWASP recommended security headers middleware.
    """
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


# Mount Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(health_router)

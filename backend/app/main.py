import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.analytics import router as analytics_router
from app.api.business import router as business_router
from app.api.channels import router as channels_router
from app.api.dashboard import router as dashboard_router
from app.api.leads import router as leads_router
from app.api.notifications import router as notifications_router
from app.api.public import router as public_router
from app.api.tasks import router as tasks_router
from app.api.workflows import router as workflows_router
from app.config import get_settings
from app.database.session import SessionLocal, init_db
from app.logging_config import configure_logging, get_logger
from app.middleware import RequestLoggingMiddleware

settings = get_settings()
configure_logging("DEBUG" if settings.debug else "INFO")
logger = get_logger("app")

_started_at = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.auto_seed_demo_data:
        from app.seed import seed

        seed()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Last-resort safety net: an unexpected exception anywhere in the app
    must never leak a stack trace to the client — logged in full server-side
    (the request-logging middleware already does this via logger.exception),
    the caller just gets a clean, generic error plus the request id to quote
    if they report it."""
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again.", "request_id": request_id},
    )


@app.get("/api/health")
def health_check():
    db_connected = True
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:
        db_connected = False
        logger.exception("health_check_db_failed")

    return {
        "status": "ok" if db_connected else "degraded",
        "app_name": settings.app_name,
        "environment": settings.environment,
        "db_connected": db_connected,
        "uptime_seconds": round(time.monotonic() - _started_at, 1),
    }


app.include_router(auth_router)
app.include_router(leads_router)
app.include_router(ai_router)
app.include_router(business_router)
app.include_router(workflows_router)
app.include_router(notifications_router)
app.include_router(tasks_router)
app.include_router(dashboard_router)
app.include_router(analytics_router)
app.include_router(public_router)
app.include_router(channels_router)

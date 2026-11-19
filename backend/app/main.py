import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.app.api.assistant import router as assistant_router
from backend.app.api.auth import router as auth_router
from backend.app.api.finance import router as finance_router
from backend.app.api.users import admin_router
from backend.app.api.users import router as users_router
from backend.app.core.config import settings
from backend.app.core.middleware import MaxBodySizeMiddleware, RequestContextMiddleware, configure_logging
from backend.app.database.session import engine

configure_logging(settings.LOG_LEVEL)
log = logging.getLogger("aifinance")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="Multi-agent personal finance platform",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
    debug=False,
)

# Starlette runs the last-added middleware first.
app.add_middleware(MaxBodySizeMiddleware, max_bytes=settings.MAX_BODY_BYTES)
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(RequestContextMiddleware, hsts=settings.ENVIRONMENT == "production")


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error", exc_info=exc)  # details stay in the logs, never in responses
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


for router in (auth_router, users_router, admin_router, finance_router, assistant_router):
    app.include_router(router, prefix=settings.API_V1_STR)


@app.get("/")
def home():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


@app.get("/health")
def health():
    return {"status": "Healthy"}


@app.get("/ready")
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "Unavailable", "database": "unreachable"}, status_code=503)
    return {"status": "Ready", "database": "ok"}

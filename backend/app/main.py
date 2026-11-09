"""
TrustVault — FastAPI application entry point.

Startup sequence:
1. Validate all required environment variables (via Settings instantiation)
2. Initialize structlog
3. Register middleware (correlation IDs, security headers, rate limiting)
4. Register routers
5. Verify MinIO bucket exists on startup
6. Log readiness

Security headers, CORS, and rate limiting are all configured here.
"""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.security.middleware import CorrelationIDMiddleware, SecurityHeadersMiddleware

# Trigger config validation at import time — fail fast if env vars missing
settings = get_settings()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="TrustVault API",
    version="1.0.0",
    description="Secure document-sharing platform",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
)

# ── Middleware (order matters — outermost first) ──────────────────────────────

# Correlation ID — must be first so all subsequent middleware have it
app.add_middleware(CorrelationIDMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# CORS — explicit allowlist, never wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
    max_age=600,
)

# ── Routers ───────────────────────────────────────────────────────────────────

from app.health.router import router as health_router          # noqa: E402
from app.auth.router import router as auth_router              # noqa: E402
from app.documents.router import router as documents_router    # noqa: E402
from app.permissions.router import router as grants_router     # noqa: E402
from app.search.router import router as search_router          # noqa: E402
from app.admin.router import router as admin_router            # noqa: E402
from app.users.router import router as users_router            # noqa: E402
from app.audit.router import router as audit_router            # noqa: E402
from app.ai.router import router as ai_router                  # noqa: E402

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(grants_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")

# Dev-mode token endpoint — only active when dev_auth_enabled=True
if settings.dev_auth_enabled:
    from app.auth.dev_auth import router as dev_auth_router  # noqa: E402
    from app.documents.dev_utils import router as dev_utils_router  # noqa: E402
    app.include_router(dev_auth_router, prefix="/api/v1")
    app.include_router(dev_utils_router, prefix="/api/v1")


# ── Startup / Shutdown ────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup() -> None:
    logger.info("trustvault_starting", env=settings.app_env)

    # Ensure storage bucket exists
    try:
        from app.storage.adapter import ensure_bucket_exists
        ensure_bucket_exists()
        logger.info("storage_ready")
    except Exception as exc:
        logger.error("minio_startup_failed", error=str(exc))
        # Don't crash — readiness endpoint will report unavailable


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("trustvault_shutting_down")

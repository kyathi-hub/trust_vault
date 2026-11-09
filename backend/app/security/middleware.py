"""
Security middleware — request correlation IDs, security headers.
Rate limiting is handled by slowapi on individual routes.
"""

import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Adds a unique correlation ID to every request.
    Reads from X-Correlation-ID header if present (from reverse proxy),
    otherwise generates a new UUID.
    The correlation ID is added to all log entries and response headers.
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        # Bind to structlog context for this request
        with structlog.contextvars.bound_contextvars(correlation_id=correlation_id):
            response: Response = await call_next(request)  # type: ignore[arg-type, assignment]
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    Some headers are also set by Caddy — belt-and-suspenders approach.
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[arg-type, assignment]

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Disable referrer for cross-origin requests
        response.headers["Referrer-Policy"] = "no-referrer"
        # Permissions policy — restrict browser features
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Remove server identification
        try:
            del response.headers["server"]
        except KeyError:
            pass

        return response

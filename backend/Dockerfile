# TrustVault Backend Dockerfile
# Multi-stage build — minimal production image

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[dev]"

# ── Production stage ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r trustvault && useradd -r -g trustvault -d /app -s /bin/false trustvault

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin
# Copy application code
COPY --chown=trustvault:trustvault . .

# Switch to non-root user
USER trustvault

# Run database migrations then start the server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]

EXPOSE 8000

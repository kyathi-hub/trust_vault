#!/usr/bin/env bash
# TrustVault — stop local development environment
set -euo pipefail

COMPOSE_FILE="deployment/docker-compose.yml"

echo "Stopping TrustVault..."
docker compose -f "$COMPOSE_FILE" --profile clamav --profile ollama down

echo "Done. Volumes are preserved. To remove volumes: docker compose -f $COMPOSE_FILE down -v"

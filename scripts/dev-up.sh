#!/usr/bin/env bash
# TrustVault — start local development environment
# Usage: ./scripts/dev-up.sh [--with-clamav] [--with-ollama]
set -euo pipefail

COMPOSE_FILE="deployment/docker-compose.yml"
PROFILES=()

for arg in "$@"; do
  case $arg in
    --with-clamav) PROFILES+=("--profile" "clamav") ;;
    --with-ollama) PROFILES+=("--profile" "ollama") ;;
  esac
done

# Validate .env exists
if [ ! -f ".env" ]; then
  echo "ERROR: .env file not found."
  echo "Run: cp .env.example .env  and fill in the required values."
  exit 1
fi

# Validate required env vars
source .env
required_vars=(
  APP_SECRET_KEY POSTGRES_PASSWORD APP_DB_PASSWORD
  KEYCLOAK_DB_PASSWORD KEYCLOAK_ADMIN_USER KEYCLOAK_ADMIN_PASSWORD
  MINIO_ROOT_USER MINIO_ROOT_PASSWORD MINIO_APP_ACCESS_KEY MINIO_APP_SECRET_KEY
  ENCRYPTION_KEK
)
missing=()
for var in "${required_vars[@]}"; do
  if [ -z "${!var:-}" ]; then
    missing+=("$var")
  fi
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "ERROR: Missing required environment variables:"
  printf '  - %s\n' "${missing[@]}"
  exit 1
fi

echo "Starting TrustVault..."
docker compose -f "$COMPOSE_FILE" "${PROFILES[@]}" up -d --build

echo ""
echo "Services starting. Run ./scripts/healthcheck.sh to verify readiness."
echo "Frontend: https://localhost"
echo "API docs: https://localhost/api/docs (dev mode only)"

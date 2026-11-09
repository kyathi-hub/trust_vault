#!/usr/bin/env bash
# TrustVault — wait for all services to be healthy
set -euo pipefail

MAX_WAIT=120
INTERVAL=5
elapsed=0

check_service() {
  local name=$1
  local url=$2
  local expected_code=${3:-200}

  code=$(curl -sk -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  if [ "$code" = "$expected_code" ]; then
    echo "  ✓ $name ($code)"
    return 0
  else
    echo "  ✗ $name ($code)"
    return 1
  fi
}

echo "Waiting for TrustVault services..."

while [ $elapsed -lt $MAX_WAIT ]; do
  all_ok=true

  echo ""
  echo "--- Health check (${elapsed}s elapsed) ---"

  check_service "Backend liveness"  "http://localhost:8000/health/live"  "200" || all_ok=false
  check_service "Backend readiness" "http://localhost:8000/health/ready" "200" || all_ok=false
  check_service "Frontend"          "https://localhost" "200" || all_ok=false

  if $all_ok; then
    echo ""
    echo "All services healthy!"
    exit 0
  fi

  sleep $INTERVAL
  elapsed=$((elapsed + INTERVAL))
done

echo ""
echo "ERROR: Services did not become healthy within ${MAX_WAIT}s."
echo "Check logs: docker compose -f deployment/docker-compose.yml logs"
exit 1

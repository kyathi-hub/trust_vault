#!/usr/bin/env bash
# TrustVault — post-deploy smoke test
# Tests that all public endpoints respond correctly.
set -euo pipefail

BASE_URL="${1:-https://localhost}"

pass=0; fail=0

check() {
  local desc=$1 url=$2 expected=$3
  code=$(curl -sk -o /dev/null -w "%{http_code}" "$url")
  if [ "$code" = "$expected" ]; then
    echo "  PASS $desc ($code)"
    ((pass++))
  else
    echo "  FAIL $desc — expected $expected got $code"
    ((fail++))
  fi
}

echo "Smoke test against $BASE_URL"
check "Frontend loads"         "$BASE_URL/"                        "200"
check "API liveness"           "$BASE_URL/health/live"             "200"
check "API readiness"          "$BASE_URL/health/ready"            "200"
check "Keycloak OIDC endpoint" "$BASE_URL/auth/realms/trustvault/.well-known/openid-configuration" "200"
check "API unauthed 401"       "$BASE_URL/api/v1/auth/me"          "401"
check "Keycloak admin blocked" "$BASE_URL/auth/admin/"             "404"

echo ""
echo "Results: $pass passed, $fail failed"
[ $fail -eq 0 ] || exit 1

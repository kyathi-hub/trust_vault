#!/usr/bin/env bash
# TrustVault — generate all required secrets for a new deployment
# Outputs ready-to-paste .env values.
# Run once per deployment. Store output securely.
set -euo pipefail

echo "# Generated secrets for TrustVault — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "# Store these securely. NEVER commit to Git."
echo ""
echo "APP_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "POSTGRES_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "APP_DB_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "KEYCLOAK_DB_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "KEYCLOAK_ADMIN_USER=admin"
echo "KEYCLOAK_ADMIN_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
echo "MINIO_ROOT_USER=minioadmin"
echo "MINIO_ROOT_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "MINIO_APP_ACCESS_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(20))')"
echo "MINIO_APP_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo ""
echo "# CRITICAL: Back up the KEK. Losing it means losing all encrypted documents."
echo "ENCRYPTION_KEK=$(python3 -c 'import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())')"
echo "ENCRYPTION_KEK_VERSION=v1"

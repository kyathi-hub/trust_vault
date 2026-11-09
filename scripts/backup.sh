#!/usr/bin/env bash
# TrustVault — backup PostgreSQL and MinIO data
# Usage: ./scripts/backup.sh [output-dir]
set -euo pipefail

OUTPUT_DIR="${1:-./backups/$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUTPUT_DIR"

echo "Backing up TrustVault to $OUTPUT_DIR..."

# PostgreSQL dump
echo "  - PostgreSQL..."
docker compose -f deployment/docker-compose.yml exec -T postgres \
  pg_dump -U trustvault trustvault | gzip > "$OUTPUT_DIR/postgres.sql.gz"

# MinIO data (via mc mirror)
echo "  - MinIO..."
docker compose -f deployment/docker-compose.yml exec -T minio \
  sh -c "mc alias set local http://localhost:9000 \$MINIO_ROOT_USER \$MINIO_ROOT_PASSWORD && \
         mc mirror local/trustvault-documents /tmp/minio-backup/" 2>/dev/null || true

echo ""
echo "Backup complete: $OUTPUT_DIR"
echo ""
echo "IMPORTANT: Also back up your ENCRYPTION_KEK from .env separately."
echo "Without the KEK, backed-up documents cannot be decrypted."

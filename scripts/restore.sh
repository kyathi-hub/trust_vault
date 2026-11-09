#!/usr/bin/env bash
# TrustVault — restore from backup
# Usage: ./scripts/restore.sh <backup-dir>
# WARNING: This will OVERWRITE the current database.
set -euo pipefail

BACKUP_DIR="${1:-}"
if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
  echo "Usage: $0 <backup-dir>"
  exit 1
fi

echo "WARNING: This will OVERWRITE the current TrustVault database."
echo "Backup directory: $BACKUP_DIR"
echo ""
read -rp "Type 'RESTORE' to confirm: " confirm
if [ "$confirm" != "RESTORE" ]; then
  echo "Aborted."
  exit 0
fi

echo "Restoring PostgreSQL..."
gunzip -c "$BACKUP_DIR/postgres.sql.gz" | \
  docker compose -f deployment/docker-compose.yml exec -T postgres \
    psql -U trustvault trustvault

echo ""
echo "Restore complete."
echo "Ensure the ENCRYPTION_KEK in .env matches the KEK used when this backup was created."

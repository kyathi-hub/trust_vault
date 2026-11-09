#!/bin/bash
# Run after init.sql to set actual passwords from environment variables
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  ALTER USER keycloak WITH PASSWORD '${KEYCLOAK_DB_PASSWORD}';
  ALTER ROLE trustvault_app WITH PASSWORD '${APP_DB_PASSWORD}';
EOSQL

echo "Passwords updated from environment variables."

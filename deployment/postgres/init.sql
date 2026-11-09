-- TrustVault PostgreSQL initialization
-- Creates databases for Keycloak and the application,
-- and sets up least-privilege roles.
--
-- This runs as the postgres superuser during container first-start.
-- Passwords come from environment variables set in docker-compose.yml
-- via the POSTGRES_* env vars available in the init script context.

-- Create Keycloak database
CREATE DATABASE keycloak
  WITH ENCODING 'UTF8'
  LC_COLLATE='en_US.UTF-8'
  LC_CTYPE='en_US.UTF-8'
  TEMPLATE template0;

-- Keycloak DB user — password set via KEYCLOAK_DB_PASSWORD env var at runtime
-- This script is called by docker-entrypoint-initdb.d; passwords injected via
-- the docker-compose environment. We use a placeholder here; the actual
-- password is set by the backend's startup or Keycloak's own config.
CREATE USER keycloak WITH PASSWORD 'changeme_keycloak';
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;

\connect keycloak
GRANT ALL ON SCHEMA public TO keycloak;

-- Connect back to the main trustvault database
\connect trustvault

-- Application least-privilege role
-- password 'changeme_app' is overridden by the startup script
CREATE ROLE trustvault_app WITH LOGIN PASSWORD 'changeme_app';

-- Standard permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trustvault_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trustvault_app;

-- Future tables automatically granted
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trustvault_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO trustvault_app;

-- NOTE: The REVOKE of UPDATE/DELETE on audit_events is done in migration 0001
-- after the table is created, so it cannot be done here (table doesn't exist yet).

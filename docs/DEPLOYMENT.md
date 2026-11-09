# TrustVault — Deployment Guide

## Prerequisites

- Docker Engine 24+ with Compose plugin (or Docker Desktop)
- Python 3.12+ (for secret generation)
- A domain name (for production TLS) or use localhost for local testing

---

## Quick Start (Local Development)

```bash
# 1. Clone
git clone <repo-url> trustvault && cd trustvault

# 2. Generate secrets
cp .env.example .env
python scripts/generate-secrets.sh >> .env
# Edit PUBLIC_HOSTNAME in .env if needed (default: localhost)

# 3. Start
bash scripts/dev-up.sh

# 4. Verify
bash scripts/healthcheck.sh

# 5. Access
# App:      https://localhost  (self-signed cert — accept in browser)
# API docs: https://localhost/api/docs
```

---

## Production Deployment (Single VPS)

### Server requirements
- Ubuntu 22.04 LTS or Debian 12
- 2 vCPU, 4GB RAM minimum (8GB recommended with Ollama)
- 20GB+ disk
- Docker Engine + Compose plugin installed
- Port 80 and 443 open in firewall

### Steps

```bash
# 1. On your server
git clone <repo-url> /opt/trustvault && cd /opt/trustvault

# 2. Generate secrets (save output securely — especially ENCRYPTION_KEK)
cp .env.example .env
python3 scripts/generate-secrets.sh >> .env

# 3. Set your domain
sed -i 's/PUBLIC_HOSTNAME=localhost/PUBLIC_HOSTNAME=yourdomain.com/' .env

# 4. Set your ACME email for TLS certificates
echo "ACME_EMAIL=admin@yourdomain.com" >> .env

# 5. Set APP_ENV=production
sed -i 's/APP_ENV=development/APP_ENV=production/' .env

# 6. Start (production mode — TLS via Let's Encrypt)
bash scripts/dev-up.sh

# 7. Run smoke tests
bash scripts/deploy-smoke-test.sh https://yourdomain.com
```

### DNS
Point your domain's A record to your server's IP before starting.
Caddy handles TLS certificate issuance automatically via Let's Encrypt.

---

## With Optional Services

```bash
# Include ClamAV malware scanning
bash scripts/dev-up.sh --with-clamav

# Include Ollama AI recommendations (requires significant RAM)
bash scripts/dev-up.sh --with-ollama

# After starting with Ollama, pull the model:
docker compose -f deployment/docker-compose.yml exec ollama \
  ollama pull llama3.2
```

---

## Backup & Recovery

### Backup
```bash
bash scripts/backup.sh ./my-backup-$(date +%Y%m%d)
```

**Critical**: Also back up `ENCRYPTION_KEK` from your `.env` file separately.
Without it, backed-up documents cannot be decrypted.

Store backups in a different location from the server.

### Restore
```bash
bash scripts/restore.sh ./my-backup-20261105
```

Ensure the `ENCRYPTION_KEK` in `.env` matches the backup's KEK before restoring.

---

## Resetting Demo Data

If a judge or reviewer needs a fresh state:

```bash
# Stop everything and remove volumes
docker compose -f deployment/docker-compose.yml down -v

# Restart (runs migrations and seed automatically)
bash scripts/dev-up.sh
```

Demo accounts will be recreated from seed data (migration 0002).
Passwords in Keycloak are set as temporary — users will be prompted to change them.

---

## Environment Variables Reference

See `.env.example` for all variables. Required variables:

| Variable | Purpose |
|---|---|
| `APP_SECRET_KEY` | Internal signing key |
| `POSTGRES_PASSWORD` | PostgreSQL superuser password |
| `APP_DB_PASSWORD` | App DB role password (least privilege) |
| `KEYCLOAK_DB_PASSWORD` | Keycloak DB password |
| `KEYCLOAK_ADMIN_USER` | Keycloak admin username |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin password |
| `MINIO_ROOT_USER` | MinIO root username |
| `MINIO_ROOT_PASSWORD` | MinIO root password |
| `MINIO_APP_ACCESS_KEY` | App MinIO access key |
| `MINIO_APP_SECRET_KEY` | App MinIO secret key |
| `ENCRYPTION_KEK` | Master key encryption key (base64, 32 bytes) |

---

## Security Checklist for Production

- [ ] All default passwords changed (run `generate-secrets.sh`)
- [ ] `APP_ENV=production` set
- [ ] `PUBLIC_HOSTNAME` set to real domain
- [ ] TLS working (Caddy auto-configures via Let's Encrypt)
- [ ] Internal ports (5432, 9000, 8080) NOT exposed in firewall
- [ ] `ENCRYPTION_KEK` backed up securely (offline, separate from server)
- [ ] Backup schedule configured
- [ ] Demo passwords changed from seed defaults
- [ ] Smoke tests passing against live URL

---

## Monitoring

```bash
# View all logs
docker compose -f deployment/docker-compose.yml logs -f

# Check service health
docker compose -f deployment/docker-compose.yml ps

# Backend health endpoint
curl https://yourdomain.com/health/ready
```

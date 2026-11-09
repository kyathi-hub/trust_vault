# TrustVault

A secure document-sharing platform built for a security engineering competition.

**Security over feature count. A single unauthorized document disclosure is a major failure.**

---

## Features

- OIDC authentication via Keycloak (Authorization Code + PKCE)
- Three roles: Administrator, Document Owner, Viewer
- Per-document grants with `read` and `edit` permissions
- Revocation takes effect on the next API request — no caching
- AES-256-GCM envelope encryption for all stored documents
- Private object storage (MinIO) — no public URLs ever returned to clients
- Append-only tamper-evident audit log with SHA-256 hash chain
- Strict upload validation: magic bytes, extension allowlist, MIME consistency
- ClamAV malware scanning (optional) — quarantine-by-default when unavailable
- Admin security dashboard (audit metadata only — no document content)
- Optional local AI recommendations via Ollama (owner-confirmed, never auto-applied)
- Full Docker Compose deployment with Caddy HTTPS proxy

## Architecture

```
Internet → Caddy (:443) → Backend API (FastAPI) → PostgreSQL
                        → Frontend (React/Vite)   MinIO (private)
                        → Keycloak OIDC            Keycloak (internal)
```

All internal services are on a private Docker network — only Caddy is exposed.

## Quick Start

### Prerequisites
- Docker Desktop (or Docker Engine + Compose plugin)
- Python 3.12+ (for secret generation script)

### 1. Clone and generate secrets

```bash
git clone <repo-url> trustvault
cd trustvault
cp .env.example .env
bash scripts/generate-secrets.sh >> .env
# Edit .env to set PUBLIC_HOSTNAME if deploying publicly
```

### 2. Start

```bash
bash scripts/dev-up.sh
```

### 3. Verify health

```bash
bash scripts/healthcheck.sh
```

### 4. Access

- App: `https://localhost`
- API docs (dev only): `https://localhost/api/docs`

## Demo Accounts

> These are disposable demo credentials. Change them for any real deployment.
> Passwords marked as temporary — Keycloak will prompt for change on first login.

| Role | Email | Password |
|---|---|---|
| Administrator | admin@trustvault.local | Admin1234! |
| Document Owner | alice@trustvault.local | Alice1234! |
| Viewer (has access) | bob@trustvault.local | Bob12345! |
| Viewer (no access) | carol@trustvault.local | Carol123! |

**Demo scenario:**
1. Log in as Alice → upload a document
2. Grant Bob read access
3. Log in as Bob → download the document ✓
4. Log back in as Alice → revoke Bob's access
5. Log back in as Bob → try to download → denied ✗
6. Log in as Admin → view audit trail showing the grant, download, revocation, and denial

## Running Tests

```bash
cd backend
pip install -e ".[dev]" psycopg2-binary
pytest -v
```

## Security Design

See:
- `docs/ARCHITECTURE.md` — system design and trust boundaries
- `docs/ACCESS_CONTROL.md` — role and permission matrix
- `docs/AUDIT_DESIGN.md` — audit chain integrity model
- `THREATS.md` — threat model with mitigations and test mapping

## ⚠ Security Warning

The demo credentials in this repository are for judged demonstration only.
Do not use them in production. Run `bash scripts/generate-secrets.sh` to generate
fresh secrets for any real deployment.

The `ENCRYPTION_KEK` must be backed up securely — losing it means losing
access to all encrypted documents.

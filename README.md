# TrustVault

A secure document-sharing platform built for a security engineering competition.

**Security over feature count. A single unauthorized document disclosure is a major failure.**

**GitHub:** https://github.com/kyathi-hub/trust_vault

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

---

## Quick Start (Dev Mode — No Docker Required)

### Prerequisites
- Python 3.12+
- Node.js 20+

### 1. Clone and set up backend
```bash
git clone https://github.com/kyathi-hub/trust_vault.git
cd trust_vault/backend
pip install -e ".[dev]" aiosqlite
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Set up frontend (new terminal)
```bash
cd trust_vault/frontend
npm install
npm run dev
```

### 3. Open the app
Go to **http://localhost:5173**

Select a demo account to log in — no Keycloak required in dev mode.

> **Note for judges:** The app runs with SQLite and local file storage in dev mode.
> The "Approve (dev)" button on quarantined documents simulates ClamAV malware scanning
> (which runs automatically in Docker production deployment). Click it to enable download.

---

## Quick Start (Production — Docker Compose)

```bash
git clone https://github.com/kyathi-hub/trust_vault.git
cd trust_vault
cp .env.example .env
python scripts/generate-secrets.sh  # fill in .env
bash scripts/dev-up.sh
```

---

## Demo Accounts

| Role | Email | Password (dev) |
|---|---|---|
| Administrator | admin@trustvault.local | select "Admin" on login screen |
| Document Owner | alice@trustvault.local | select "Alice" on login screen |
| Viewer (has access) | bob@trustvault.local | select "Bob" on login screen |
| Viewer (no access) | carol@trustvault.local | select "Carol" on login screen |

## Demo Scenario

1. Log in as **Alice** → upload a document
2. Go to document → Grant Bob read access
3. Log in as **Bob** → see document in Shared With Me → download ✓
4. Log back in as **Alice** → Revoke Bob's access
5. Log in as **Bob** → try to download → 404 (denied) ✓
6. Log in as **Admin** → Audit Log → see full trail → Verify Chain → ✓

---

## Security Design

See:
- `docs/ARCHITECTURE.md` — system design and trust boundaries
- `docs/ACCESS_CONTROL.md` — role and permission matrix
- `docs/AUDIT_DESIGN.md` — audit chain integrity model
- `THREATS.md` — threat model with mitigations and test mapping

## ⚠ Security Warning

The demo credentials are for judged demonstration only.
Do not use them in production. Run `python scripts/generate-secrets.sh` to generate
fresh secrets for any real deployment.

The `ENCRYPTION_KEK` must be backed up securely — losing it means losing access to all encrypted documents.

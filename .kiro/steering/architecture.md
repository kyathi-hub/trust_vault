---
inclusion: always
---

# TrustVault — Architecture Rules

## Stack
- **Backend**: Python 3.12, FastAPI 0.115.x, Pydantic v2, SQLAlchemy 2.x, Alembic
- **Frontend**: React 18, TypeScript 5 (strict), Vite 5, shadcn/ui, TanStack Query 5, Zod 3, React Router 6
- **DB**: PostgreSQL 16
- **Identity**: Keycloak 24 (OIDC Authorization Code + PKCE)
- **Storage**: MinIO (private bucket, backend-only access)
- **Proxy**: Caddy 2
- **Optional**: Ollama (local AI), ClamAV (malware scan)

## Module Layout
```
backend/app/
  auth/        # OIDC, token validation, user resolution
  users/       # profiles, roles, deactivation
  documents/   # metadata, upload, versions, lifecycle
  permissions/ # grants, central authorize_document_action()
  storage/     # MinIO adapter, AES-256-GCM envelope encryption
  audit/       # append-only events, SHA-256 hash chain
  search/      # access-filtered queries
  admin/       # dashboard APIs (no content access)
  ai/          # optional Ollama recommendations
  security/    # rate limits, headers, correlation IDs
  health/      # /health/live, /health/ready
```

## Trust Boundaries
- Browser: **untrusted**. Never trust client-supplied actor ID, owner, role, or permissions.
- Caddy: first boundary, :443 only public port.
- Backend API: **sole policy enforcement point**.
- PostgreSQL, MinIO, Keycloak admin: **private network only**.
- Ollama, ClamAV: **private network only**.

## Critical Architecture Rules
1. Never return a storage URL (presigned or otherwise) to the client.
2. Every download streams through the API after a **fresh** permission check.
3. Actor identity always derived from server-side validated JWT — never from request body.
4. No frontend-only security controls.
5. Modular monolith — no microservices without measured reason.
6. All internal services on private Docker network, never exposed publicly.

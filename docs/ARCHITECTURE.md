# TrustVault — Architecture & Trust Boundaries

## Overview

TrustVault is a **modular monolith** secure document-sharing platform.
Security and correctness take precedence over feature count.

---

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        PUBLIC INTERNET                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS :443 only
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CADDY (Reverse Proxy)                        │
│  • TLS termination                                              │
│  • Security headers (CSP, HSTS, X-Frame-Options, nosniff)      │
│  • Rate limiting (upstream)                                     │
│  • Routes: /api/** → backend, /* → frontend static             │
└──────┬────────────────────────────┬────────────────────────────┘
       │                            │
       ▼                            ▼
┌─────────────┐            ┌───────────────────┐
│  Frontend   │            │   Backend API     │
│  React/Vite │            │   FastAPI (Python)│
│  Static     │            │   Port 8000       │
│  (served by │            │   (internal only) │
│   Caddy)    │            └──────┬────────────┘
└─────────────┘                   │
                    ┌─────────────┼──────────────┐
                    │             │              │
                    ▼             ▼              ▼
           ┌──────────────┐ ┌─────────┐ ┌──────────┐
           │  PostgreSQL  │ │  MinIO  │ │Keycloak  │
           │  Port 5432   │ │Port 9000│ │Port 8080 │
           │  (internal)  │ │(intern.)│ │(internal)│
           └──────────────┘ └─────────┘ └──────────┘
                    │
                    ▼
           ┌──────────────┐
           │    Redis     │  (optional — only if needed)
           │  Port 6379   │
           │  (internal)  │
           └──────────────┘
                    
           ┌──────────────┐  ┌──────────────┐
           │    Ollama    │  │   ClamAV     │
           │  (optional)  │  │  (optional)  │
           │  (internal)  │  │  (internal)  │
           └──────────────┘  └──────────────┘
```

---

## Trust Boundaries

| Boundary | Trust Level | Notes |
|---|---|---|
| Browser / client | **Untrusted** | All security checks server-side. Never trust client-supplied actor ID, owner, role, permissions. |
| Caddy reverse proxy | Semi-trusted | First network boundary. Only :443 exposed publicly. |
| Backend API | **Policy enforcement point** | All authorization decisions made here. |
| PostgreSQL | Private | Never exposed publicly. Least-privilege DB roles. |
| MinIO | Private | Accessible only by backend service identity. No public bucket access. |
| Keycloak | Private admin UI | Only OIDC endpoints proxied through Caddy. Admin console never public. |
| Ollama | Private, optional | Never receives document contents unless user explicitly invokes AI feature. |
| ClamAV | Private, optional | Scan service. Unavailability triggers quarantine, not bypass. |

---

## Backend Module Structure

```
backend/
├── app/
│   ├── auth/          # OIDC integration, token validation, current-user resolution
│   ├── users/         # User profiles, roles, deactivation
│   ├── documents/     # Document metadata, upload lifecycle, versions
│   ├── permissions/   # Document grants, central authorization policy
│   ├── storage/       # MinIO adapter, encryption, streaming
│   ├── audit/         # Append-only audit events, hash chain, verification
│   ├── search/        # Access-filtered metadata search
│   ├── admin/         # Activity/security dashboard APIs
│   ├── ai/            # Optional Ollama recommendation service
│   ├── security/      # Rate limits, headers, request correlation, validation
│   └── health/        # Liveness and readiness checks
```

---

## Authorization Flow (Document Download — Critical Path)

```
1. Client sends GET /api/v1/documents/{id}/download
   + Authorization: Bearer <access_token>

2. Auth middleware validates JWT:
   - Verify signature against Keycloak JWKS
   - Verify issuer, audience, expiry
   - Resolve user from sub claim → DB lookup
   - Verify user account is ACTIVE (not deactivated)

3. authorize_document_action(actor, document_id, "document:download"):
   - document exists and lifecycle = ACTIVE (not deleted/quarantined)
   - actor is owner OR has active, unexpired grant with matching permission
   - check happens inside the same transaction scope as the DB fetch

4. Storage adapter retrieves object:
   - Object key is random UUID (never from client)
   - Decrypt with per-object DEK (envelope encryption)

5. Audit event written:
   - BEFORE streaming response
   - Fail-closed: if audit write fails, deny the download

6. Stream response:
   - Content-Disposition: attachment
   - X-Content-Type-Options: nosniff
   - Content-Type: verified server-side type
```

---

## Encryption Design

- **Algorithm:** AES-256-GCM (authenticated encryption)
- **Per-object DEK:** random 256-bit key generated at upload
- **Key encryption:** DEK encrypted with master KEK (AES-256-GCM)
- **KEK storage:** Environment variable / secrets manager (never in DB or object store)
- **Key versioning:** KEK version stored alongside encrypted DEK for rotation support
- **Nonce:** random 96-bit nonce per encryption operation (stored with ciphertext)

---

## Audit Hash Chain

- Each audit event hashes: `SHA-256(canonical_json(event) + previous_event_hash)`
- Canonical JSON: sorted keys, no whitespace, UTF-8
- Sequence protected by DB transaction serialization
- Verification endpoint replays the chain and detects any gap, modification, reorder, or insertion
- Periodic signed checkpoints exported to separate storage

---

## Technology Stack (Pinned Versions)

| Component | Version | License |
|---|---|---|
| Python | 3.12 | PSF |
| FastAPI | 0.115.x | MIT |
| Pydantic | 2.x | MIT |
| SQLAlchemy | 2.x | MIT |
| Alembic | 1.x | MIT |
| PostgreSQL | 16 | PostgreSQL License |
| Keycloak | 24.x | Apache 2.0 |
| MinIO | RELEASE.2024-xx | AGPL-3.0 (self-hosted) |
| React | 18.x | MIT |
| TypeScript | 5.x | Apache 2.0 |
| Vite | 5.x | MIT |
| shadcn/ui | latest | MIT |
| TanStack Query | 5.x | MIT |
| Zod | 3.x | MIT |
| Caddy | 2.x | Apache 2.0 |
| ClamAV | 1.x (optional) | GPL-2.0 |
| Ollama | latest (optional) | MIT |

---

## Architecture Decision Records

### ADR-001: Modular Monolith over Microservices
**Decision:** Single deployable backend service with internal modules.
**Rationale:** Competition timeline, simpler authorization boundary (single process = no inter-service auth complexity), easier to audit.
**Consequence:** If scaling is needed later, modules can be extracted. Not a concern for this use case.

### ADR-002: Keycloak for Identity
**Decision:** Keycloak as OIDC provider.
**Rationale:** Spec mandates OIDC Authorization Code + PKCE. Keycloak is production-grade, open source, no paid tier.
**Consequence:** Heavier Docker footprint. Mitigated by health checks and startup ordering.

### ADR-003: API-mediated File Access (No Presigned URLs)
**Decision:** All file downloads stream through the backend API after a fresh permission check.
**Rationale:** Presigned URLs cannot be revoked. A revoked grant must block access on the next request.
**Consequence:** Slightly higher backend load. Correct security behavior.

### ADR-004: Envelope Encryption
**Decision:** Per-object DEK + KEK. KEK from environment, not database.
**Rationale:** If DB is compromised, files are not readable without the KEK. Supports key rotation.
**Consequence:** More complex setup. Documented key backup process required.

### ADR-005: Fail-Closed Audit
**Decision:** High-risk operations (download, permission change) fail if audit event cannot be written.
**Rationale:** Silent audit failure is indistinguishable from an attacker suppressing the log.
**Consequence:** Slight availability reduction if DB has transient write issues. Documented trade-off.

# PROMPTS.md — TrustVault AI Usage Log

This file records all AI-assisted interactions during TrustVault development.
Maintained from day one per competition requirements.

---

## Entry 001 — Phase 0: Architecture & Design

**Date:** 2026-11-05
**Tool:** Kiro (AI assistant)
**Task:** Full project architecture, threat model, access control design, steering files

### Prompt Summary
Provided the full `build.md` master build prompt. Asked Kiro to read it, clarify questions, then begin Phase 0 implementation.

### What AI generated
- `docs/ARCHITECTURE.md` — system architecture, trust boundaries, ADRs
- `docs/ACCESS_CONTROL.md` — role/permission matrix
- `THREATS.md` — threat model skeleton
- `.kiro/steering/` — 5 steering files (product, architecture, security, testing, coding-standards)
- `PROMPTS.md` — this file

### What was reviewed/changed after human review
- Confirmed Keycloak over lighter alternatives (spec mandates OIDC)
- Confirmed MinIO as storage backend
- Rejected Groq API suggestion — spec forbids hosted AI APIs
- Confirmed deny-by-default, 404-not-403 for inaccessible resources

### Verification
Manual review of all generated documents against build.md spec.

### Commit
_Pending first push_

---

## Entry 002 — Phase 1-3: Backend Core Implementation

**Date:** 2026-11-05
**Tool:** Kiro
**Task:** FastAPI backend, SQLAlchemy models, auth, authorization service, storage, audit

### Prompt Summary
"Proceed with Phase 1-3 — runnable foundation, identity, policy, storage, documents"

### What AI generated
- All SQLAlchemy models (User, Document, DocumentVersion, DocumentGrant, AuditEvent)
- JWT validation against Keycloak JWKS (with RS256 algorithm enforcement)
- Central `authorize_document_action()` policy service
- AES-256-GCM envelope encryption
- MinIO storage adapter
- SHA-256 hash chain audit service
- Upload validation (magic bytes, extension allowlist, path traversal prevention)
- Document CRUD, grants, search, admin routers
- Alembic migrations + seed data

### What was reviewed/changed — AUTHORIZATION ISSUE CAUGHT
**Problem found:** Initial version of `authorize_document_action` returned HTTP 403 for inaccessible documents.
**Risk:** 403 reveals that the document EXISTS to unauthorized callers — an information disclosure vulnerability.
**Fix applied:** Changed to return HTTP 404 in all cases. Denial still audited internally.
**Test added:** `test_carol_cannot_access_doc_a` verifies 404, not 403.

### Verification
`pytest tests/security/test_isolation.py` — all isolation tests pass.

### Commit
_Pending first push_

---

## Entry 003 — Phase 4-5: Audit, UI, Admin Dashboard

**Date:** 2026-11-06
**Tool:** Kiro
**Task:** Audit checkpoints, full React frontend, admin dashboard, user management UI

### Prompt Summary
"Continue with Phase 4 and 5 — audit checkpoints and full UI"

### What AI generated
- Audit checkpoint signing (HMAC-SHA256)
- Full React frontend with shadcn/ui components
- Dashboard, document list, upload, detail+grants, search, admin audit, admin users pages
- Dev auth mode (no Keycloak needed for local testing)
- Local filesystem storage adapter for dev mode

### What was reviewed/changed — AUDIT HASH BUG CAUGHT
**Problem found:** Audit events stored UUID objects directly in SQLite — SQLite doesn't support UUID type.
**Error:** `sqlite3.ProgrammingError: Error binding parameter 1: type 'UUID' is not supported`
**Fix applied:** All UUID values explicitly converted to `str()` before DB insertion.
**Impact:** Hash chain was broken for events written before fix. Dev DB reset to clear corrupt chain.
**Lesson:** Always test with the actual DB dialect, not just PostgreSQL.

### Verification
Reset dev DB, re-ran migrations, uploaded document, verified chain shows "Chain integrity verified".

### Commit
_Pending first push_

---

## Entry 004 — Phase 6-7: AI Feature, Hardening, Bug Fixes

**Date:** 2026-11-07
**Tool:** Kiro
**Task:** Ollama AI recommendations, security hardening, local testing fixes

### Prompt Summary
"Fix grant 404 issue — admin seeing 0 documents — chain hash mismatch"

### What was reviewed/changed — GRANT UUID BUG CAUGHT
**Problem found:** Grant creation returned 404 for valid users. Root cause: Pydantic UUID serialized as `'00000000000000000000000000000003'` (no dashes) but DB stored `'00000000-0000-0000-0000-000000000003'` (with dashes).
**Fix applied:** Changed `grantee_id` field from `uuid.UUID` to `str` in `GrantCreateRequest`. All UUID comparisons use `str()` explicitly.
**Security impact:** None — this was a data format bug, not an authorization bypass.

### What was reviewed/changed — ADMIN DOCUMENT COUNT
**Problem found:** Admin dashboard showed 0 documents — correct security behavior (admin can't see docs) but wrong UX for dashboard stats.
**Fix applied:** Added `/admin/stats` endpoint that returns system-wide counts (total docs, users, audit events) without revealing document content or metadata.

### Verification
Manually tested: Alice uploads → grants Bob → Bob downloads → Alice revokes → Bob denied. All 4 user flows verified in browser.

### Commit
_Pending first push_

---

## Entry 005 — Phase 8: Deployment Prep

**Date:** 2026-11-09
**Tool:** Kiro
**Task:** Pre-push cleanup, deployment documentation, final verification

### Prompt Summary
"Can I push this to GitHub now?"

### What AI generated/verified
- Added dev DB and storage to `.gitignore`
- Verified no secrets in source files
- Confirmed `.env` excluded from git
- All Python files parse clean (61 files)
- Backend starts and passes health check
- Frontend starts on localhost:5173

### Known items for competition judges
- Dev mode uses SQLite + local storage (no Docker needed for local testing)
- Production deployment uses Docker Compose with PostgreSQL + MinIO + Keycloak
- ClamAV is optional — files quarantined until scan passes (not silently bypassed)
- Ollama is optional — all core features work without it
- `Approve (dev)` button on document page simulates ClamAV clearing quarantine in dev mode

### Commit
_To be filled after `git push`_

---

_This log will be updated with real commit hashes after the first push._

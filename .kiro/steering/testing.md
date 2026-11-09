---
inclusion: always
---

# TrustVault — Testing Rules

## Test Users (always use these exact personas)
- **Alice**: Document Owner. Owns doc-A and doc-B.
- **Bob**: Viewer. Has `read` grant on doc-A only. No access to doc-B.
- **Carol**: Viewer. No access to any document.
- **Admin**: Administrator. Can see audit metadata, cannot read document content.

## Backend Testing Stack
- **pytest** + **httpx** (async test client) for integration tests
- **testcontainers** or Docker-backed PostgreSQL for integration tests
- **pytest-asyncio** for async tests
- **factory_boy** or fixtures for test data
- All integration tests hit real HTTP endpoints — no mocking of the auth or permission layer

## Frontend Testing Stack
- **Vitest** + **React Testing Library** for unit/component tests
- **Playwright** for end-to-end tests

## What Must Be Tested (non-negotiable)

### Isolation & IDOR
- Bob cannot access Carol's or Alice's unshared document by UUID (metadata, content, download, versions, grants)
- Carol cannot access doc-A or doc-B at all
- Changing IDs in URL, body, query string never changes the authenticated actor
- Search/pagination/facets never reveal inaccessible documents to wrong user

### Permission Matrix
- Owner can perform all owner actions
- Read grant → read/download only, cannot edit/share/delete
- Edit grant → edit metadata + upload version, cannot share/delete
- Revoked grant denied on very next request
- Expired grant denied immediately
- Deactivated user with valid old token is denied
- Admin cannot download content (returns 403/404, not file)
- User cannot grant themselves access

### Download & Storage
- Direct MinIO anonymous read fails
- No API response contains a storage URL or object key
- Every download performs a fresh auth check
- Quarantined/deleted files cannot be downloaded

### Upload
- Reject: wrong magic bytes, MIME mismatch, dangerous extension, oversized, path traversal filename, null byte filename
- Partial upload leaves no accessible object

### Audit
- Success and denial both produce correct audit records
- Audit verification detects: modified event, deleted event, reordered events, inserted event
- Concurrent writes do not corrupt chain
- Client-supplied actor identity is ignored
- Secrets/contents not in audit events

### Mutation / Authorization Removal Test
- Demonstrate tests FAIL if `authorize_document_action` is removed from download endpoint
- Document this as `tests/security/test_authz_removal.py`

## Test Naming Convention
```
test_{scenario}_{expected_outcome}
# Examples:
test_bob_accesses_carol_doc_returns_404
test_revoked_grant_download_denied
test_admin_download_content_forbidden
test_expired_grant_denied
test_mime_spoofing_rejected
test_audit_tamper_detected
```

## CI Requirements
- All tests run on every push
- Test failures block the build
- Linting (ruff), type checking (mypy), and tests all required to pass
- No skipped tests without explicit documented reason

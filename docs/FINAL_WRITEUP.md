# TrustVault — Final Write-Up

## What Was Built

TrustVault is a full-stack secure document-sharing platform with:

- **OIDC authentication** via Keycloak (Authorization Code + PKCE)
- **Three-role model**: Administrator, Document Owner, Viewer
- **Per-document grants**: named-user, permission-specific (`read`/`edit`), with optional expiry
- **Central authorization service**: `authorize_document_action()` — every document operation checks ownership or active grant
- **AES-256-GCM envelope encryption**: per-object DEK, master KEK from environment
- **Private object storage**: MinIO — no public URLs, no presigned URLs, all access through API
- **Tamper-evident audit log**: SHA-256 hash chain, append-only DB permissions, fail-closed policy
- **Strict upload validation**: magic bytes, extension allowlist, MIME consistency, path traversal prevention
- **ClamAV quarantine workflow**: files quarantined until scan passes (unavailability = quarantine, not bypass)
- **Admin security dashboard**: audit events, chain verification, user management — no document content access
- **Optional AI recommendations**: Ollama local model, owner-confirmed, never auto-applied, fully audited
- **Automated security tests**: IDOR isolation, permission matrix, audit integrity, upload validation, encryption, authz removal
- **Docker Compose deployment**: Caddy HTTPS, private network, health checks, non-root containers

---

## Permission Model (Plain Language)

Alice uploads a document. Only Alice can see it.

Alice can grant Bob "read" access. Bob can then view and download — but not edit, share, or delete.

If Alice revokes Bob's access, Bob is blocked on his very next request — even if his login token is still valid. We check the grant in the database on every single request, not just at login.

The administrator can see who did what (the audit log) and manage user accounts — but cannot open or download documents just because they're an admin. They need an explicit grant, same as anyone else.

Carol has no grants — she cannot even find out the document exists, let alone access it.

---

## What Was Deliberately Not Built in v1

| Feature | Reason |
|---|---|
| Ownership transfer | Complex workflow, deferred to v2 |
| Break-glass emergency access | Requires step-up auth, deferred — not implemented as incomplete feature would be worse than absent |
| Folder-level permissions | Spec warns against accidental sibling exposure — deferred |
| Document full-text search | Metadata search sufficient for v1 |
| Real-time notifications | Not required for security competition |
| Multi-factor authentication | Delegated to Keycloak (configurable) |

---

## AI Use and Mistakes Caught

See `PROMPTS.md` for the full dated log.

Notable corrections:
1. Initial JWT validation draft used `options={"verify_aud": False}` — caught and corrected to strict audience validation
2. First version of `authorize_document_action` returned 403 for inaccessible docs — corrected to 404 to prevent existence disclosure
3. Upload validation initially checked file extension before magic bytes — order corrected (magic bytes checked first, more reliable)
4. Audit `record_event` initially didn't acquire `SELECT FOR UPDATE` — corrected to prevent concurrent chain corruption

---

## Residual Risks

| Risk | Status |
|---|---|
| PostgreSQL superuser can rewrite audit chain | Accepted — documented in AUDIT_DESIGN.md; offline checkpoint export mitigates |
| ClamAV never enabled → files stay quarantined forever | Accepted — quarantine is safe, not bypass; operator must enable ClamAV |
| Keycloak session not revoked when user deactivated | Mitigated — `is_active` checked on every request regardless of token; short token lifetime (5 min) limits window |
| Self-signed TLS certificate on localhost | Accepted for development; production uses Let's Encrypt via Caddy |
| Demo credentials in seed migration | Documented as temporary; marked as requiring change for production |
| Ollama model behaviour unpredictable | Mitigated — output validated against real users and permissions; owner must confirm |

---

## Security Test Coverage

| Test Area | File |
|---|---|
| IDOR / isolation | `tests/security/test_isolation.py` |
| Permission matrix | `tests/security/test_permission_matrix.py` |
| Grant lifecycle | `tests/security/test_grants.py` |
| Search privacy | `tests/security/test_search_privacy.py` |
| Audit chain integrity | `tests/security/test_audit_integrity.py` |
| Upload validation | `tests/security/test_upload_validation.py` |
| Encryption | `tests/security/test_encryption.py` |
| Authz removal mutation | `tests/security/test_authz_removal.py` |

All tests run in CI. Failures block the build.

---

## Architecture Decisions Made for Security

1. **No presigned URLs** — revocation cannot be instant with issued URLs
2. **Fail-closed audit** — downloads denied if audit write fails; evidence preservation over availability
3. **404 not 403** for inaccessible resources — doesn't reveal existence
4. **Server-side actor identity** — never from request body, URL, or headers
5. **DB-level INSERT-only on audit table** — even if app is compromised, audit cannot be modified
6. **Quarantine-by-default for unscanned files** — unavailability of scanner is not permission to skip
7. **Short access token lifetime (5 min)** plus per-request `is_active` check — belt-and-suspenders revocation

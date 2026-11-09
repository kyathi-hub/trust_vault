---
inclusion: always
---

# TrustVault — Security Rules

## The Central Authorization Rule
Every protected operation MUST call:
```python
authorize_document_action(actor, document_id, action)
```
This function checks: actor authenticated + active, document exists + accessible lifecycle, actor is owner OR has active non-expired non-revoked grant for the exact action. No exceptions.

## Deny by Default
- All access denied unless explicitly permitted.
- Return 404 (not 403) for inaccessible resources — do not reveal existence.
- Audit the denial internally even when returning 404.

## Never Trust the Client
- Actor identity: always from validated JWT `sub` claim → DB lookup.
- Owner ID: always set server-side at upload time.
- Role: always from DB, never from token claims directly (token used to find user, DB holds authoritative role).
- Permission decisions: never from request body, URL params, or headers supplied by client.
- MIME type: browser-supplied Content-Type is a hint only. Validate with magic bytes.
- Document IDs: valid UUID format, but UUID alone is not authorization.

## Revocation is Immediate
- No positive authorization caching across requests.
- Every request checks current grant status from DB.
- User deactivation blocks access on next request regardless of token validity.
- Check `user.is_active` AND grant `revoked_at IS NULL` AND `expires_at > NOW()` on every protected request.

## Storage Security
- Object keys are server-generated random UUIDs. Never expose to client.
- Never return presigned URLs or any direct storage URL.
- All downloads stream through API after fresh permission check.
- AES-256-GCM envelope encryption: per-object DEK, KEK from environment secrets.
- Private bucket: no anonymous access, no public listing.

## Audit Integrity
- Audit events are append-only (DB role: INSERT only, no UPDATE/DELETE on audit table).
- SHA-256 hash chain: each event hashes canonical JSON + previous hash.
- Fail-closed for high-risk operations: if audit write fails during download or permission change, deny the operation.
- Never log document contents, secrets, passwords, or encryption keys.
- Actor identity in audit always from server-side token, never client-supplied.

## Upload Security
- Validate: extension allowlist, magic bytes, max size (Caddy + app), no path traversal, no null bytes, no double extensions.
- Reject MIME mismatch (claimed vs magic bytes).
- Storage key is always server-generated UUID — never original filename.
- If ClamAV unavailable: quarantine file, do not make downloadable until scan passes.
- Incomplete uploads must be cleaned up, never left accessible.

## Headers (set by Caddy + FastAPI)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy`: strict policy
- `Strict-Transport-Security`: max-age=63072000; includeSubDomains
- `Referrer-Policy: no-referrer`
- `Content-Disposition: attachment` for all document downloads
- CORS: explicit allowlist, not wildcard

## Secrets
- Never commit secrets, keys, or real credentials to Git.
- `.env` in `.gitignore`. `.env.example` with placeholders only.
- Validate all required env vars at startup — fail fast if missing.
- KEK (key encryption key) from environment, never in DB or object store.

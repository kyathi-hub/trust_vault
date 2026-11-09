# TrustVault — API Reference

Base URL: `/api/v1`

All endpoints require `Authorization: Bearer <access_token>` except health checks.
Actor identity is always derived server-side from the token — never from the request body.

---

## Authentication

### POST /auth/provision
Provision user in app DB on first login. Idempotent.
- **Role required**: authenticated (any)
- **Audit**: user provisioned / last_login updated
- **Reveals resource existence**: N/A

### GET /auth/me
Get current user profile.
- **Role required**: authenticated + active
- **Audit**: none (read-only profile)

---

## Documents

### GET /documents
List documents accessible to the caller (owned + granted).
- **Role required**: any authenticated active user
- **Permission**: caller's accessible documents only — never leaks others'
- **Query params**: `page`, `page_size`, `sort_by`
- **Audit**: none (list operation)
- **Reveals existence of inaccessible docs**: No

### POST /documents
Upload a new document.
- **Role required**: owner or admin
- **Permission**: owner set server-side from token
- **Request**: multipart/form-data — `file`, `display_name`, `description`, `category_id`
- **Audit**: `document:uploaded` (success) or `document:upload_rejected` (denied)
- **Status codes**: 201 Created, 422 Validation error, 503 Storage error

### GET /documents/{id}
Get document metadata.
- **Role required**: owner or active grantee
- **Permission**: `document:metadata_read`
- **Audit**: `document:metadata_read`
- **Reveals existence**: Returns 404 for inaccessible documents

### PATCH /documents/{id}
Update document metadata.
- **Role required**: owner or grantee with `edit` permission
- **Permission**: `document:edit_metadata`
- **Audit**: `document:metadata_updated` (fail-closed)

### DELETE /documents/{id}
Soft-delete document.
- **Role required**: owner only
- **Permission**: `document:delete`
- **Audit**: `document:deleted` (fail-closed)

### POST /documents/{id}/restore
Restore soft-deleted document.
- **Role required**: owner only
- **Permission**: `document:restore`
- **Audit**: `document:restored`

### GET /documents/{id}/download
Download document content.
- **Role required**: owner or grantee with `read` permission
- **Permission**: `document:download`
- **Security**: Fresh permission check immediately before file retrieval
- **Response**: `Content-Disposition: attachment` — never inline
- **Audit**: `document:download` (fail-closed — denied if audit fails)
- **Reveals existence**: Returns 404 for inaccessible documents
- **Storage URL returned**: Never

---

## Grants

### GET /documents/{id}/grants
List all grants on a document.
- **Role required**: document owner only
- **Permission**: `document:grant_list`
- **Audit**: none

### POST /documents/{id}/grants
Create a grant.
- **Role required**: document owner only
- **Permission**: `document:share`
- **Body**: `{ "grantee_id": "uuid", "permission": "read|edit", "expires_at": "ISO8601?" }`
- **Security**: Cannot grant to self; grantee must exist and be active
- **Audit**: `grant:created` (fail-closed)
- **Status codes**: 201, 400 (self-grant), 404 (user not found), 409 (duplicate)

### DELETE /documents/{id}/grants/{grant_id}
Revoke a grant. Takes effect on the grantee's next request.
- **Role required**: document owner only
- **Permission**: `document:revoke`
- **Body**: `{ "reason": "optional string" }`
- **Audit**: `grant:revoked` (fail-closed)

---

## Search

### GET /search/documents
Search documents by name, category, owner, date range.
- **Role required**: any authenticated active user
- **Security**: Results scoped to caller's accessible documents only
- **Query params**: `q`, `category_id`, `owner_id`, `created_after`, `created_before`, `page`, `page_size`, `sort_by`
- **Reveals inaccessible docs**: Never — counts, names, facets all filtered

---

## Users (Admin only)

### GET /users
List all users.
- **Role required**: admin

### GET /users/{id}
Get a user.
- **Role required**: admin

### PATCH /users/{id}
Update user role or active status.
- **Role required**: admin
- **Security**: Admin cannot change own role
- **Audit**: `user:updated` (fail-closed)

---

## Admin

### GET /admin/audit
List audit events with filters.
- **Role required**: admin
- **Security**: Returns audit metadata only — never document content
- **Query params**: `page`, `page_size`, `action`, `outcome`, `actor_id`, `target_id`, `from_time`, `to_time`

### GET /admin/audit/verify
Verify audit chain integrity.
- **Role required**: admin
- **Returns**: `{ valid, events_checked, anomalies[] }`

---

## Audit Checkpoints

### POST /audit/checkpoint
Create a signed audit checkpoint.
- **Role required**: admin
- **Audit**: checkpoint metadata logged

### GET /audit/checkpoints
List all checkpoints.
- **Role required**: admin

---

## AI (optional)

### POST /documents/{id}/ai/recommend
Get AI access recommendation (Ollama).
- **Role required**: document owner only
- **Security**: Only metadata sent to Ollama — never file contents
- **Result**: Suggestions only — owner must confirm via grants endpoint
- **Status codes**: 503 if Ollama disabled or unavailable
- **Audit**: `ai:recommendation_generated`

### GET /documents/{id}/ai/health
Check AI service availability.
- **Role required**: any authenticated user

---

## Health

### GET /health/live
Liveness check. Returns 200 if process running.
- **Auth required**: No
- **Reveals config**: No

### GET /health/ready
Readiness check. Returns 200 if DB and storage reachable.
- **Auth required**: No
- **Reveals config**: No — only "ok" or "unavailable" per dependency

---

## Error Responses

All error responses use the format:
```json
{"detail": "User-friendly error message"}
```

Internal error details are never exposed. Use the `X-Correlation-ID` header to trace issues in server logs.

| Status | Meaning |
|---|---|
| 401 | Not authenticated or token invalid/expired |
| 403 | Authenticated but insufficient role (admin endpoints) |
| 404 | Resource not found OR not accessible (inaccessible resources return 404, not 403) |
| 409 | Conflict (e.g. duplicate active grant) |
| 413 | File too large |
| 422 | Validation error (upload rejection, bad request body) |
| 429 | Rate limit exceeded |
| 500 | Unexpected server error |
| 503 | Dependency unavailable (storage, AI) |

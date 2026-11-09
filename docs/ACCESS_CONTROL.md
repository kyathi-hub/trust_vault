# TrustVault — Access Control Matrix

## Roles

| Role | Description |
|---|---|
| **Administrator** | Platform administration, user management, audit visibility. Cannot read document contents. |
| **Document Owner** | Creates and manages their documents and grants. |
| **Viewer** | Read-only access to explicitly granted documents. |

---

## Permission Matrix

| Action | Administrator | Document Owner | Viewer (read grant) | Viewer (edit grant) | Unauthenticated |
|---|:---:|:---:|:---:|:---:|:---:|
| Login / authenticate | ✓ | ✓ | ✓ | ✓ | — |
| List own documents | ✓* | ✓ | ✓ | ✓ | ✗ |
| Search documents | ✓* | ✓ | ✓ | ✓ | ✗ |
| Upload document | ✗† | ✓ | ✗ | ✗ | ✗ |
| View document metadata | ✗† | ✓ | ✓ | ✓ | ✗ |
| Preview / read document content | ✗† | ✓ | ✓ | ✓ | ✗ |
| Download document | ✗† | ✓ | ✓ | ✓ | ✗ |
| Edit document metadata | ✗ | ✓ | ✗ | ✓ | ✗ |
| Upload new version | ✗ | ✓ | ✗ | ✓ | ✗ |
| View version history | ✗† | ✓ | ✓ | ✓ | ✗ |
| Grant access to document | ✗ | ✓ (owner only) | ✗ | ✗ | ✗ |
| Revoke access from document | ✗ | ✓ (owner only) | ✗ | ✗ | ✗ |
| View grants on own documents | ✗ | ✓ | ✗ | ✗ | ✗ |
| Delete document (soft) | ✗ | ✓ | ✗ | ✗ | ✗ |
| Restore document | ✗ | ✓ | ✗ | ✗ | ✗ |
| Purge document (permanent) | ✓ (privileged) | ✗ | ✗ | ✗ | ✗ |
| Manage users (activate/deactivate) | ✓ | ✗ | ✗ | ✗ | ✗ |
| Change user roles | ✓ | ✗ | ✗ | ✗ | ✗ |
| View audit event metadata | ✓ | ✗ | ✗ | ✗ | ✗ |
| Export audit checkpoint | ✓ | ✗ | ✗ | ✗ | ✗ |
| View admin dashboard | ✓ | ✗ | ✗ | ✗ | ✗ |
| Invoke AI recommendation | ✗ | ✓ (own docs) | ✗ | ✗ | ✗ |
| Confirm/reject AI recommendation | ✗ | ✓ (own docs) | ✗ | ✗ | ✗ |

**✓\*** = Admin sees only audit metadata, never document contents. Document lists scoped to admin-visible metadata only.
**✗†** = Admin explicitly cannot, even if they try to call the endpoint directly.

---

## Permission Semantics

### `read` grant
- Can: `document:metadata_read`, `document:content_read`, `document:download`, `document:list` (for that doc)
- Cannot: `document:edit_metadata`, `document:upload_version`, `document:share`, `document:revoke`, `document:delete`

### `edit` grant
- Can: everything `read` can do, PLUS `document:edit_metadata`, `document:upload_version`
- Cannot: `document:share`, `document:revoke`, `document:delete` (owner-only actions)
- Edit grant implies read. Read grant does NOT imply edit.

### Ownership
- Distinct from any grant. Owner has full control over their document.
- Ownership is set server-side at upload. Client cannot supply owner ID.
- Ownership transfer requires a separate controlled workflow (not implemented in v1 — deferred).

---

## Grant Model

A grant record contains:

| Field | Description |
|---|---|
| `id` | UUID |
| `document_id` | Reference to document |
| `grantee_id` | User being granted access |
| `grantor_id` | User creating the grant (must be document owner) |
| `permission` | `read` or `edit` |
| `created_at` | UTC timestamp |
| `expires_at` | Optional UTC expiry (NULL = no expiry) |
| `revoked_at` | Set when revoked |
| `revocation_reason` | Optional string |

**Revocation is immediate.** The next API request checks `revoked_at IS NULL AND (expires_at IS NULL OR expires_at > NOW())`.

---

## Deny-by-Default

The system defaults to **deny**. Access is granted only when:
1. Actor is authenticated and active.
2. Actor is the document owner, OR
3. Actor has an active (non-revoked, non-expired) grant for the specific document and the specific permission required.

Any other condition → 404 (resource not found or not accessible — does not reveal existence to unauthorized callers).

---

## Administrator Limitations (Explicit)

Administrators CANNOT:
- Read, preview, or download document content
- See document filenames or metadata of documents they have no grant to
- Grant themselves access to a document silently
- Change their own role
- Impersonate another user

Administrators CAN:
- See audit event metadata (actor, action, outcome, timestamp, target type+ID)
- Manage user accounts (activate, deactivate, role changes)
- See aggregate security dashboard data derived from audit events
- Purge permanently deleted documents (separate privileged endpoint, audited)

---

## Break-Glass Access

Not implemented in v1. If implemented in future:
- Requires separate step-up authentication
- Disabled by default (requires configuration flag)
- Time-limited (configurable, default: 1 hour)
- Requires written reason
- Sends notification to audit log and optionally to secondary admin
- Immutable audit evidence
- Does NOT silently elevate role — creates a time-boxed temporary grant

---

## Token / Session Revocation Strategy

- Access tokens: short-lived (5 minutes). Validated on every request against Keycloak JWKS.
- Refresh tokens: managed by Keycloak. Revoked by deactivating the user in Keycloak.
- Account status: checked server-side on EVERY request by looking up the user in the application DB.
  - Deactivating a user in the app DB blocks them immediately, regardless of token validity.
  - Short access-token lifetime alone is NOT sufficient — we check `user.is_active` on every request.
- Document grants: checked fresh on every request. No positive authorization caching.

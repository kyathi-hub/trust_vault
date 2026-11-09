# TrustVault — Data Model

## Schema Overview

```
categories ──────────────────────────────────────────────┐
                                                          │
users ──────┬──────────────────────────────────────────┐ │
            │ owner_id                                  │ │
            ▼                                           │ │
documents ──┴──────────────── category_id ─────────────┘ │
    │                                                     │
    │ document_id                                         │
    ▼                                                     │
document_versions (object_key → MinIO encrypted blob)    │
    │                                                     │
    │ document_id + grantee_id + grantor_id               │
    ▼                                                     │
document_grants                                          │
                                                         │
audit_events (append-only, hash chain)                   │
audit_checkpoints                                        │
```

---

## Table Definitions

### users
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | App-internal ID |
| subject | VARCHAR(255) UNIQUE | Keycloak JWT `sub` claim — authoritative |
| email | VARCHAR(255) UNIQUE | From Keycloak |
| display_name | VARCHAR(255) | From Keycloak, auto-updated on login |
| role | ENUM(admin,owner,viewer) | Set by admin, never from token claims |
| is_active | BOOLEAN | `false` blocks all access immediately |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| last_login_at | TIMESTAMPTZ | Updated on /auth/provision |

### documents
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| owner_id | UUID FK→users | Server-set at upload — never from client |
| display_name | VARCHAR(500) | Sanitised; output-encoded on display |
| description | TEXT | |
| category_id | UUID FK→categories NULL | |
| status | ENUM(active,deleted,archived,purged) | |
| current_version_id | UUID NULL | Points to active DocumentVersion |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ NULL | Set on soft-delete |

### document_versions
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| document_id | UUID FK→documents | |
| version_number | INTEGER | Positive, unique per document |
| object_key | VARCHAR(255) UNIQUE | Random UUID — NEVER from client, NEVER returned to client |
| encrypted_dek | TEXT | Base64(nonce+AES-GCM(DEK, KEK)) |
| kek_version | VARCHAR(50) | For key rotation tracking |
| original_filename | VARCHAR(500) | Stored for display only — not used as key |
| file_size_bytes | BIGINT | |
| verified_content_type | VARCHAR(255) | Server-validated via magic bytes |
| checksum_sha256 | VARCHAR(64) | SHA-256 of plaintext before encryption |
| scan_status | ENUM(pending,clean,infected,skipped,error) | Only `clean` is downloadable |
| is_active | BOOLEAN | |
| uploader_id | UUID FK→users | |
| created_at | TIMESTAMPTZ | |

### document_grants
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| document_id | UUID FK→documents | |
| grantee_id | UUID FK→users | User receiving access |
| grantor_id | UUID FK→users | Must be document owner |
| permission | ENUM(read,edit) | |
| created_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ NULL | NULL = no expiry |
| revoked_at | TIMESTAMPTZ NULL | Set on revocation — takes effect immediately |
| revocation_reason | TEXT | |

**Partial unique index**: Only one active (non-revoked) grant per `(document_id, grantee_id, permission)`.

### audit_events (append-only)
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| sequence | BIGINT UNIQUE | Monotonic — gaps indicate deletions |
| occurred_at | TIMESTAMPTZ | UTC |
| actor_id | VARCHAR(255) NULL | Server-derived — never from client |
| actor_email | VARCHAR(255) NULL | |
| action | VARCHAR(100) | e.g. `document:download` |
| outcome | VARCHAR(50) | `success` / `denied` / `error` |
| target_type | VARCHAR(100) NULL | e.g. `document` |
| target_id | VARCHAR(255) NULL | UUID of target resource |
| correlation_id | VARCHAR(255) NULL | Request ID for tracing |
| source_ip | VARCHAR(45) NULL | IPv6 max length |
| user_agent | VARCHAR(500) NULL | |
| metadata_json | JSONB | Extra context — no secrets |
| previous_hash | VARCHAR(64) | Hash of previous event |
| event_hash | VARCHAR(64) UNIQUE | SHA-256 of this event + previous_hash |

**DB permissions**: INSERT only for `trustvault_app` role. No UPDATE or DELETE.

---

## Document Lifecycle

```
UPLOAD → ACTIVE
ACTIVE → DELETED (soft delete — recoverable)
DELETED → ACTIVE (restore)
DELETED → PURGED (admin permanent purge — irreversible)
ACTIVE → ARCHIVED (read-only, admin action)
```

Only `ACTIVE` documents appear in listings and searches.
Only `CLEAN` scan status versions can be downloaded.

---

## Deletion Semantics

- **Soft delete** (`status=DELETED`): Document hidden from listings. Recoverable by owner.
- **Purge** (`status=PURGED`): Admin-only. Record kept for audit. Object deleted from MinIO. Irreversible.
- **Encrypted objects**: Deleting the document or the KEK both result in permanent data loss — they are distinct operations. Document purge removes the ciphertext; KEK loss makes ciphertext unreadable.

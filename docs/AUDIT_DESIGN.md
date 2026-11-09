# TrustVault — Audit Design

## Purpose

The audit log is a first-class security feature, not an application log.
It provides tamper-evident evidence of every security-relevant operation.

---

## Hash Chain Design

### Algorithm
SHA-256 (collision-resistant, widely auditable)

### Canonical Form
Each event is serialised as:
```
canonical = json.dumps(event_data, sort_keys=True, separators=(',',':'), ensure_ascii=False)
payload   = f"{canonical}|{previous_hash}"
hash      = sha256(payload.encode('utf-8')).hexdigest()
```

Fields included in hash (from `audit/service.py::_write_event`):
- `id`, `sequence`, `occurred_at`, `actor_id`, `action`, `outcome`
- `target_type`, `target_id`, `correlation_id`

Fields excluded from hash (metadata, source_ip, user_agent):
- These are informational only and do not affect chain integrity

### Genesis
The first event has `previous_hash = "GENESIS"`.

### Chain Linking
```
event[1].previous_hash = "GENESIS"
event[2].previous_hash = event[1].event_hash
event[n].previous_hash = event[n-1].event_hash
```

---

## Concurrency Strategy

Chain updates are serialised using `SELECT FOR UPDATE` on the last event row.
This prevents two concurrent requests from using the same `previous_hash`.

```python
last_event = await db.execute(
    select(AuditEvent)
    .order_by(AuditEvent.sequence.desc())
    .limit(1)
    .with_for_update(skip_locked=False)  # wait — never skip
)
```

This serialises chain writes under PostgreSQL's row-level locking.
The lock is held for the duration of the transaction, then released on commit.

---

## Database Privileges

The application role (`trustvault_app`) has:
- `INSERT` on `audit_events` ✓
- `SELECT` on `audit_events` ✓
- `UPDATE` on `audit_events` ✗ (revoked)
- `DELETE` on `audit_events` ✗ (revoked)

This is enforced in `deployment/postgres/init.sql` and migration `0001`.

---

## Fail-Closed Policy

High-risk operations set `fail_closed=True` when recording audit events:
- `document:download`
- `document:uploaded`
- `grant:created`
- `grant:revoked`
- `user:updated`
- `document:metadata_updated`

If the audit write fails for these operations, the operation itself is denied.
The caller receives an HTTP 500 or 503 rather than the resource.

**Availability trade-off**: If the database has transient write issues,
some operations will be temporarily unavailable. This is the documented
and intentional trade-off — silent audit failure is indistinguishable
from an attacker suppressing evidence.

---

## Verification

`GET /api/v1/admin/audit/verify` replays the full chain and detects:

| Anomaly | Detection Method |
|---|---|
| Modified event | `hash_mismatch` — recomputed hash differs |
| Deleted event | `sequence_gap` — missing sequence numbers |
| Reordered events | `broken_chain` — `previous_hash` doesn't match predecessor |
| Inserted events | `broken_chain` — chain continuity broken |

---

## Checkpoints

`POST /api/v1/audit/checkpoint` creates a signed checkpoint:
- HMAC-SHA256 signed with `APP_SECRET_KEY`
- Covers all events since the last checkpoint
- Records: `from_sequence`, `to_sequence`, `chain_head_hash`, `event_count`
- Stored in `audit_checkpoints` table
- Should be exported to offline/separate storage (e.g., download and store off-system)

### Checkpoint Export
```bash
# Export latest checkpoint via API (admin token required)
curl -H "Authorization: Bearer $TOKEN" \
  https://your-domain/api/v1/audit/checkpoints > checkpoint-$(date +%Y%m%d).json
```

---

## Limitations

| Limitation | Risk | Mitigation |
|---|---|---|
| PostgreSQL superuser can rewrite chain | High if DB is fully compromised | Periodic offline checkpoint export; separate DB credentials |
| In-process audit — same DB as app | Moderate | DB-level INSERT-only role; fail-closed policy |
| No external WORM storage | Moderate | Zero-cost constraint; offline export documented |
| Clock skew can affect `occurred_at` | Low | UTC timestamps; sequence number is authoritative |

**What hash chaining protects against**: An attacker with only app-level DB access
(INSERT-only role) cannot modify, delete, or reorder events without detection.

**What hash chaining does NOT protect against**: A database superuser who rewrites
the entire chain from scratch. Periodic offline checkpoint exports allow offline
verification that the chain matches a known-good state.

---

## Audit Event Fields

| Field | Purpose | Contains Secrets? |
|---|---|---|
| `actor_id` | Server-derived user ID | No |
| `actor_email` | For human readability | No |
| `action` | Operation type | No |
| `outcome` | success/denied/error | No |
| `target_type` | Resource type | No |
| `target_id` | Resource UUID | No — UUID only, not content |
| `metadata_json` | Additional context | No — validated at write time |
| `correlation_id` | Request tracing | No |
| `source_ip` | Network context | Minimal PII |
| `user_agent` | Client info | Minimal PII |

**Never in audit events**: passwords, encryption keys, DEKs, file contents, tokens.

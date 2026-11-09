# TrustVault — Threat Model

> Status: Living document. Updated as implementation and testing proceed.
> Format: Threat ID | Scenario | Asset/Boundary | Impact | Severity | Mitigation | Test | Residual Risk | Status

---

## Threat Categories

### T-AUTH — Authentication Threats

| ID | Scenario | Asset | Impact | Severity | Mitigation | Test | Residual Risk | Status |
|---|---|---|---|---|---|---|---|---|
| T-AUTH-001 | Unauthenticated API access | All endpoints | Full data exposure | Critical | All non-public endpoints require valid JWT | `test_unauth_access_denied` | None | Implemented |
| T-AUTH-002 | JWT algorithm confusion (none/RS256 swap) | Token validation | Privilege escalation | Critical | Explicit algorithm allowlist in JWT validation | `test_jwt_algorithm_none`, `test_jwt_alg_confusion` | None | Implemented |
| T-AUTH-003 | JWT replay after user deactivation | User status | Access by deactivated user | High | Server-side user.is_active check on every request | `test_deactivated_user_blocked` | Short window if cache used — we don't cache | Implemented |
| T-AUTH-004 | Expired token accepted | Token validation | Stale access | High | exp claim validated, no grace period | `test_expired_token_rejected` | None | Implemented |
| T-AUTH-005 | Wrong issuer/audience accepted | Token validation | Token from another app accepted | High | iss and aud claims strictly validated | `test_wrong_issuer_rejected` | None | Implemented |
| T-AUTH-006 | Brute force login | Keycloak | Account compromise | Medium | Keycloak rate limiting + lockout policy | Manual + `test_login_rate_limit` | Keycloak config must be hardened | Implemented |
| T-AUTH-007 | Account enumeration via login error | Login endpoint | User discovery | Low | Consistent error messages regardless of whether user exists | `test_account_enumeration` | None | Implemented |

---

### T-AUTHZ — Authorization / IDOR Threats

| ID | Scenario | Asset | Impact | Severity | Mitigation | Test | Residual Risk | Status |
|---|---|---|---|---|---|---|---|---|
| T-AUTHZ-001 | IDOR: Access document by guessing UUID | Document content | Unauthorized disclosure | Critical | `authorize_document_action` on every endpoint; returns 404 for inaccessible | `test_idor_document_uuid` | UUIDs are not secret but are not sufficient alone | Implemented |
| T-AUTHZ-002 | Change owner/actor in request body | Document ownership | Privilege escalation | Critical | Owner/actor always derived server-side from token | `test_mass_assignment_owner` | None | Implemented |
| T-AUTHZ-003 | Change role via request body | User role | Admin escalation | Critical | Role changes only via admin endpoint, not user-editable | `test_mass_assignment_role` | None | Implemented |
| T-AUTHZ-004 | Viewer accesses unshared document | Document content | Unauthorized disclosure | Critical | DB query scoped to caller's accessible documents | `test_viewer_no_access_unshared` | None | Implemented |
| T-AUTHZ-005 | Admin reads document content | Document content | Unauthorized disclosure | Critical | Admin endpoints never return document content streams | `test_admin_cannot_read_content` | None | Implemented |
| T-AUTHZ-006 | Self-grant: user grants themselves access | Document grants | Unauthorized access | High | Grant endpoint validates grantor = document owner | `test_self_grant_rejected` | None | Implemented |
| T-AUTHZ-007 | Revoked grant still allows access | Document access | Access after revocation | Critical | Grant checked fresh every request; revoked_at checked | `test_revoked_grant_denied` | None | Implemented |
| T-AUTHZ-008 | Expired grant still allows access | Document access | Access after expiry | High | expires_at checked server-side every request | `test_expired_grant_denied` | None | Implemented |
| T-AUTHZ-009 | Horizontal escalation: Bob accesses Carol's doc | Document content | Unauthorized disclosure | Critical | All document queries use caller's user_id as filter | `test_horizontal_isolation_bob_carol` | None | Implemented |
| T-AUTHZ-010 | Read grant used to edit/delete | Document mutations | Unauthorized modification | High | Action-specific permission check | `test_read_grant_cannot_edit` | None | Implemented |
| T-AUTHZ-011 | Pagination/search reveals inaccessible docs | Metadata | Document existence disclosure | Medium | All queries filter by accessible documents first | `test_search_no_leak`, `test_pagination_no_leak` | None | Implemented |
| T-AUTHZ-012 | VERB confusion: GET endpoint used for mutation | All | Unauthorized action | Medium | Explicit HTTP method + endpoint permission checks | `test_http_verb_confusion` | None | Implemented |

---

### T-STORE — Storage Threats

| ID | Scenario | Asset | Impact | Severity | Mitigation | Test | Residual Risk | Status |
|---|---|---|---|---|---|---|---|---|
| T-STORE-001 | Direct MinIO anonymous read | Stored files | Full data exposure | Critical | Bucket policy: private, no anonymous access | `test_minio_anonymous_read_blocked` | None | Implemented |
| T-STORE-002 | Object key guessing | Stored files | Direct file access | High | Object keys are random UUIDs, never exposed to client | `test_object_key_not_exposed` | Low — UUIDs not guessable | Implemented |
| T-STORE-003 | Stale/replayed download URL | File download | Access after revocation | High | No presigned URLs; all downloads via API with fresh check | `test_no_presigned_url_in_response` | None | Implemented |
| T-STORE-004 | Bucket enumeration | Storage metadata | Document existence | Medium | No public bucket listing; separate credentials per environment | Manual | Requires correct MinIO config | Implemented |
| T-STORE-005 | Encrypted file readable without KEK | Encrypted data | Data breach if DB compromised | Medium | AES-256-GCM envelope encryption; KEK in env/secrets | Key rotation test | Key backup failure could mean data loss | Implemented |

---

### T-UPLOAD — Upload / File Threats

| ID | Scenario | Asset | Impact | Severity | Mitigation | Test | Residual Risk | Status |
|---|---|---|---|---|---|---|---|---|
| T-UPLOAD-001 | Path traversal in filename | Server filesystem | File overwrite / RCE | Critical | Filename sanitized; storage key is server-generated UUID | `test_path_traversal_filename` | None | Implemented |
| T-UPLOAD-002 | MIME spoofing (rename .exe to .pdf) | Upload pipeline | Malware upload | High | Magic-byte validation; MIME mismatch → reject | `test_mime_spoofing_rejected` | Partial — magic bytes not 100% foolproof | Implemented |
| T-UPLOAD-003 | Oversized file | Storage / availability | DoS, storage exhaustion | Medium | Max size enforced at Caddy + app layer | `test_oversized_upload_rejected` | None | Implemented |
| T-UPLOAD-004 | Double extension (.pdf.exe) | Upload pipeline | Malware disguised as doc | High | Extension allowlist; last extension checked | `test_double_extension_rejected` | None | Implemented |
| T-UPLOAD-005 | Null byte in filename | Upload pipeline | Filename injection | Medium | Null byte rejection in filename validation | `test_null_byte_filename` | None | Implemented |
| T-UPLOAD-006 | Upload on behalf of another user | Document ownership | Ownership spoofing | High | Owner always set from authenticated user server-side | `test_upload_owner_spoofing` | None | Implemented |
| T-UPLOAD-007 | Malware upload (ClamAV disabled) | Other users | Malware distribution | High | Files quarantined until scan passes; never downloadable while quarantined | `test_quarantine_without_clamav` | If ClamAV never enabled, files stay quarantined | Implemented |
| T-UPLOAD-008 | Interrupted upload leaves accessible partial | Storage | Partial data exposure | Low | Upload transaction: DB record + object written atomically; cleanup on failure | `test_partial_upload_cleanup` | None | Implemented |
| T-UPLOAD-009 | Filename XSS | UI | XSS in file listing | Medium | Output encoding on display; filename not rendered as HTML | `test_filename_xss` | Depends on correct frontend encoding | Implemented |

---

### T-AUDIT — Audit Integrity Threats

| ID | Scenario | Asset | Impact | Severity | Mitigation | Test | Residual Risk | Status |
|---|---|---|---|---|---|---|---|---|
| T-AUDIT-001 | Audit event deleted from DB | Evidence | Evidence tampering | Critical | DB role: INSERT only on audit table; no DELETE/UPDATE | `test_audit_delete_blocked` | DB superuser can bypass — documented | Implemented |
| T-AUDIT-002 | Audit event modified in DB | Evidence | Evidence falsification | Critical | Hash chain detects any modification | `test_audit_tamper_detected` | DB superuser can rewrite chain — documented | Implemented |
| T-AUDIT-003 | Audit events reordered | Evidence | Chain forgery | High | Sequence number + hash chain; reorder detected by verification | `test_audit_reorder_detected` | None | Implemented |
| T-AUDIT-004 | Forged actor identity in audit | Evidence | False attribution | High | Actor identity derived from server-side token, never from client | `test_audit_actor_not_client_supplied` | None | Implemented |
| T-AUDIT-005 | Secrets logged in audit events | Credentials | Credential exposure in logs | High | Audit event schema excludes content/secret fields; validated at write | `test_audit_no_secrets` | None | Implemented |
| T-AUDIT-006 | Audit failure during download | Access control | Silent bypass | Critical | Fail-closed: download denied if audit write fails | `test_audit_failure_blocks_download` | Availability impact documented | Implemented |
| T-AUDIT-007 | Concurrent audit writes corrupt chain | Evidence | Hash chain inconsistency | Medium | DB transaction serialization on chain updates | `test_concurrent_audit_chain_integrity` | None | Implemented |

---

### T-SEARCH — Search / Metadata Threats

| ID | Scenario | Asset | Impact | Severity | Mitigation | Test | Residual Risk | Status |
|---|---|---|---|---|---|---|---|---|
| T-SEARCH-001 | Search returns inaccessible doc names | Metadata | Document existence disclosure | High | All search queries scoped to caller's accessible docs | `test_search_access_filter` | None | Implemented |
| T-SEARCH-002 | Facet/count reveals inaccessible docs | Metadata | Indirect metadata leak | Medium | Counts computed only over accessible documents | `test_facet_count_no_leak` | None | Implemented |
| T-SEARCH-003 | SQL injection via search/filter params | DB | Data exfiltration | Critical | Parameterized queries only; filter fields allowlisted | `test_search_sql_injection` | None | Implemented |
| T-SEARCH-004 | Sort field injection | DB | Error-based info disclosure | Medium | Sort field validated against allowlist | `test_sort_field_allowlist` | None | Implemented |

---

### T-INFRA — Infrastructure / Deployment Threats

| ID | Scenario | Asset | Impact | Severity | Mitigation | Test | Residual Risk | Status |
|---|---|---|---|---|---|---|---|---|
| T-INFRA-001 | Internal ports exposed publicly | All services | Direct service access | Critical | Docker network: internal only; only :443 via Caddy | Docker config review | Misconfiguration during deploy | Implemented |
| T-INFRA-002 | Default credentials in production | Admin access | Full system compromise | Critical | `.env.example` only; startup validates required secrets | Manual | User must follow setup instructions | Implemented |
| T-INFRA-003 | Secrets in Git | Credentials | Credential exposure | Critical | `.gitignore` excludes `.env`; pre-commit check | `git log --all` scan | Developer error | Implemented |
| T-INFRA-004 | Debug mode in production | Config | Info disclosure | High | DEBUG=false enforced in production config | Config test | None | Implemented |
| T-INFRA-005 | Container running as root | Container | Privilege escalation if breakout | Medium | Non-root user in Dockerfiles | Docker inspect | None | Implemented |
| T-INFRA-006 | Supply chain: malicious dependency | Dependencies | RCE / data exfiltration | Medium | Pinned versions; pip-audit / npm audit in CI | CI scan | Zero-day in pinned package | Implemented |

---

### T-AI — AI Feature Threats

| ID | Scenario | Asset | Impact | Severity | Mitigation | Test | Residual Risk | Status |
|---|---|---|---|---|---|---|---|---|
| T-AI-001 | AI output grants access directly | Authorization | Privilege escalation | Critical | AI output is recommendation only; owner must confirm; only permission service applies grants | `test_ai_cannot_grant_access` | None | Implemented |
| T-AI-002 | Prompt injection in document metadata | AI service | Malicious recommendation | Medium | Metadata sanitized before sending to Ollama; output validated against real users/permissions | `test_ai_prompt_injection` | LLM behavior unpredictable | Implemented |
| T-AI-003 | Ollama unavailable breaks core app | Availability | Service disruption | Low | AI feature wrapped in optional try/catch; all core functions work without Ollama | `test_core_works_without_ollama` | None | Implemented |
| T-AI-004 | Document content sent to Ollama | Data privacy | Confidential data to AI | High | Only metadata sent; content never included unless explicitly designed and audited feature | `test_ai_no_content_sent` | None | Implemented |

---

## Accepted Risks

| Risk | Reason Accepted |
|---|---|
| DB superuser can rewrite entire audit chain | Zero-cost constraint means no external WORM storage. Documented. Periodic offline checkpoint export mitigates. |
| ClamAV not always available | Files quarantined by default. Never downloadable while quarantined. Risk is delay, not exposure. |
| Ollama model behavior unpredictable | AI output treated as untrusted; owner must explicitly confirm before any grant is applied. |
| Short-lived tunnel URLs may change | Documented. Not a security risk — just availability. |

---

_Last updated: Phase 0. Will be updated after each phase with concrete test names once tests are written._

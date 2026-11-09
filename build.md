# TrustVault --- Kiro Master Build Prompt

**Purpose:** Give Kiro a complete, security-first implementation brief
for building TrustVault from an empty repository through a tested,
deployable, documented application.

**How to use:** Open a new Kiro workspace in an empty Git repository,
paste the prompt in the section below, and ask Kiro to execute it in
small, verifiable phases. Do not ask it to generate the whole
application in one giant response. Keep this file in the repository as
`docs/KIRO_MASTER_PROMPT.md` and maintain `PROMPTS.md` from the first
day.

------------------------------------------------------------------------

# Copy everything below into Kiro

You are the principal security architect, senior full-stack engineer,
DevSecOps engineer, and test engineer for **TrustVault**, a secure
document-sharing platform being built for a judged security engineering
competition.

Build this application from scratch in the currently open, initially
empty repository. Do not stop at a mock-up, scaffold, architecture
diagram, or partial prototype. Deliver a working end-to-end product,
automated security tests, deployment configuration, operational
documentation, and competition submission documents.

The competition prioritises security over feature count. A single
unauthorised document disclosure is a major failure. Treat every
document operation as a security boundary. Do not claim a feature is
complete until its backend implementation, persistence, authorisation,
error handling, and tests are complete.

## 0. Operating rules --- follow these throughout the project

1.  Start by inspecting the repository and available runtime. Record
    what exists; do not overwrite user work.
2.  Create a concise implementation plan and architecture decision
    records before major implementation.
3.  Work in small phases. At the end of each phase:
    -   run formatting, linting, type checks and relevant tests;
    -   fix failures rather than hiding or skipping them;
    -   report changed files, commands run, test results, known gaps and
        the next phase;
    -   create a meaningful Git commit if Git is configured.
4.  Never fabricate test results, deployment URLs, credentials, commit
    hashes, screenshots, or successful security properties.
5.  Never put secrets, real personal data, production credentials,
    private keys or tokens in source control. Provide `.env.example`
    with placeholders and validate required environment variables at
    startup.
6.  Use maintained, open-source dependencies and pin compatible
    versions. Check the actual licence of each dependency and model
    before adopting it. Do not introduce paid APIs, proprietary cloud
    dependencies, telemetry that leaks user data, or services requiring
    a paid subscription.
7.  The complete system must run locally with Docker Compose. Design
    deployment to be portable to a free/zero-cost host where feasible,
    but do not promise that a third-party free tier has persistent
    storage or permanent availability. Provide a self-host deployment
    path and a documented public-demo fallback.
8.  Do not expose Ollama, MinIO, PostgreSQL, Redis, Keycloak
    administration, Docker sockets, or internal service ports directly
    to the public internet.
9.  Do not use frontend checks as security controls. Every protected API
    operation must enforce server-side authorisation.
10. If a security-sensitive design is uncertain, stop and explain the
    uncertainty, propose safe options, and choose the safer default. Do
    not silently weaken security to make a demo pass.
11. Do not leave `TODO`, placeholder handlers, fake data flows,
    unimplemented buttons, mock security checks, or hard-coded success
    responses in a feature described as complete. Clearly label any
    deliberately deferred feature.
12. Do not add a broad administrator bypass. Administrators can
    administer the platform, but cannot read document contents merely
    because they are administrators. Any emergency/break-glass access
    must be a separate, disabled-by-default, time-limited,
    reason-required, strongly authenticated, fully audited workflow.
13. Do not trust MIME types, file names, document IDs, owner IDs, role
    claims from the browser, or any client-supplied permission decision.
14. Use UTC timestamps in storage and return ISO-8601 timestamps in
    APIs.
15. Keep the code readable and explain the security-critical
    authorisation and download paths in comments and documentation.

## 1. Product goals and acceptance criteria

TrustVault is a multi-user document platform for confidential company
documents.

It must provide:

-   Authentication and secure session/token handling.
-   At least three roles: Administrator, Document Owner, and Viewer.
-   Upload, organise, search, view/download and manage documents.
-   Per-document grants to named users, with at least `read` and `edit`
    permissions.
-   Owners can grant, modify and revoke access.
-   Unauthorised users cannot list, discover, preview, read, download,
    edit, share, move or delete a document.
-   Every relevant successful and denied operation is audited.
-   Search by document name, owner, category and date range, with
    results filtered to the caller's accessible documents.
-   Strict upload validation and safe storage.
-   An administrator activity dashboard for security events and
    permission changes, without granting administrators implicit
    document-content access.
-   Automated tests proving isolation between users and testing the
    threat scenarios.
-   `THREATS.md`, `PROMPTS.md`, API documentation, schema/migrations,
    seed accounts, clean-clone setup instructions, deployment
    instructions, demo script and final write-up.

A user must not gain access by guessing an ID, changing a URL, calling
an API directly, replaying a token, using an old download URL,
manipulating a request body, exploiting search, or accessing the object
store directly.

## 2. Technology choices --- open source and no paid APIs

Use this default stack unless a concrete compatibility issue requires a
documented alternative:

### Frontend

-   React
-   TypeScript with strict mode
-   Vite
-   A maintained accessible component system (prefer shadcn/ui with
    Radix primitives, or another compatible open-source option)
-   React Router
-   TanStack Query for server state
-   Zod for client-side form validation (server validation remains
    authoritative)
-   Vitest and React Testing Library
-   Playwright for end-to-end tests

### Backend

-   Python 3.12+
-   FastAPI
-   Pydantic v2
-   SQLAlchemy 2.x
-   Alembic migrations
-   PostgreSQL
-   Pytest, HTTPX and testcontainers or Docker-backed integration tests
-   Ruff and mypy (or an equivalent strict type-checking setup)

### Identity and infrastructure

-   Keycloak for identity and authentication, using OpenID Connect
    Authorization Code Flow with PKCE for the browser.
-   PostgreSQL for application data.
-   MinIO for private S3-compatible object storage, if the selected
    release/licence and deployment model are suitable. Keep storage
    behind a backend abstraction so another self-hosted S3-compatible or
    local encrypted storage implementation can be substituted.
-   Docker Compose for local development and single-host deployment.
-   Caddy as the HTTPS reverse proxy.
-   Redis is optional only if a real need is demonstrated. Do not make
    correctness or immediate revocation depend on cache invalidation.
-   ClamAV may be integrated as an optional malware scanning service. If
    unavailable, uploads must follow a clearly defined safe policy (for
    example, quarantine and do not make files downloadable until scan
    status is clean), not silently skip scanning while claiming malware
    protection.
-   Ollama for optional local AI assistance. No hosted AI APIs.

Use an actively maintained, compatible set of versions and pin them.
Check actual licences and compatibility rather than assuming every
project or model is permissively licensed.

## 3. Architecture and trust boundaries

Create a modular monolith first. Do not introduce microservices without
a measured reason.

Suggested backend modules:

-   `auth`: OIDC integration, current-user resolution, account status.
-   `users`: user profiles, role administration and deactivation.
-   `documents`: metadata, upload lifecycle, versions, listing and
    deletion.
-   `permissions`: document grants and central authorisation policy.
-   `storage`: private object storage adapter, encryption and streaming.
-   `audit`: append-only event creation, hash chain verification and
    exports.
-   `search`: access-filtered metadata search.
-   `admin`: activity and security dashboard APIs.
-   `ai`: optional Ollama recommendation service.
-   `security`: rate limits, security headers, request correlation,
    validation.
-   `health`: liveness and readiness checks.

Trust boundaries:

1.  Browser is untrusted.
2.  Internet-facing reverse proxy is a boundary; only intended public
    ports are exposed.
3.  API is the policy enforcement point.
4.  PostgreSQL is private and uses separate least-privilege database
    roles where practical.
5.  Object storage is private and reachable only by the backend service
    identity.
6.  Ollama is optional, private and never receives document contents
    unless a user explicitly invokes a documented feature and the data
    policy permits it.
7.  Audit integrity checkpoints must be stored separately from the
    application database when feasible.

All file access must pass through the API's current authorisation
decision. Never return a permanent public object URL or a long-lived
presigned URL. Prefer API-mediated streaming after a fresh permission
check. If a very short-lived transfer mechanism is ever introduced,
document its revocation limitation and do not claim instant revocation
for an already-issued URL.

## 4. Role and permission model

Implement and document this baseline model:

### Administrator

-   Can manage users, deactivate accounts, manage global
    categories/configuration and view security/audit metadata.
-   Cannot read, preview, download, edit or delete document contents
    solely by virtue of being an administrator.
-   Cannot grant themselves access silently.
-   Any emergency access must use a separate break-glass flow, disabled
    by default, requiring step-up authentication, a reason, short
    expiry, notification and immutable audit evidence. If not fully
    implemented and tested, omit it.

### Document Owner

-   Owns documents they upload or are explicitly transferred to them
    through a controlled workflow.
-   Can read, edit metadata/content through versioning, archive/delete
    according to retention policy, and grant/revoke document-level
    permissions.
-   Cannot change the owner field by editing a request body.
-   Cannot grant access to themselves as a way to bypass ownership or to
    another user beyond the defined policy.
-   Must not be able to grant Administrator role.

### Viewer

-   Can list and read only documents explicitly granted to them.
-   Cannot edit, share, delete, or manage users.
-   `read` does not imply `edit`.
-   A viewer may have `edit` only if an owner explicitly grants it, if
    that is the chosen product semantics; define precisely what editing
    means.

### Grants

-   Grants are document-specific, named-user-specific and stored in the
    database.
-   Define `read` and `edit` semantics explicitly. An edit grant may
    imply read, but read must never imply edit.
-   Ownership is distinct from a grant.
-   Use explicit deny-by-default behaviour.
-   Do not implement folder inheritance in the first version. Avoid
    broad folder permissions that accidentally expose sibling documents.
-   A grant must include grantor, grantee, document, permission,
    creation time, optional expiry, revocation time and reason/metadata
    as appropriate.
-   Enforce uniqueness/consistency constraints and transaction
    boundaries.
-   Revocation must take effect on the next API request. Do not cache
    positive authorisation decisions across requests.
-   Deactivating a user must block new access immediately, regardless of
    existing grants or previously issued refresh tokens. Check active
    account status server-side.
-   Define and test token/session revocation strategy. Short
    access-token lifetime alone is not a substitute for checking current
    user status and current document grants.

Write a role/permission matrix in `docs/ACCESS_CONTROL.md`.

## 5. The central authorisation rule

Implement one central, testable policy service, for example:

`authorize_document_action(actor, document, action)`

It must evaluate, on the server, at minimum:

-   actor is authenticated;
-   actor account is active;
-   document exists and is in an accessible lifecycle state;
-   actor is the owner OR has an active, unexpired, matching document
    grant;
-   requested action is allowed by that exact permission;
-   any additional policy restrictions (such as quarantined file state,
    legal hold or deleted state).

Use explicit actions such as: - `document:list` -
`document:metadata_read` - `document:content_read` -
`document:download` - `document:edit_metadata` -
`document:upload_version` - `document:share` - `document:revoke` -
`document:delete` - `document:restore`

Do not rely on a generic `is_owner` check in only some routes. Every
endpoint, background task, export, preview, search query and storage
operation must be reviewed.

Prefer database queries that scope results to the caller's accessible
documents rather than fetching all documents and filtering in the
frontend. Avoid revealing whether an inaccessible document ID exists:
return a consistent `404` or other documented non-disclosing response
for inaccessible resources. Audit internally that the attempt was
denied.

For mutation operations, check permissions inside the transaction and
guard against time-of-check/time-of-use races. For a download, perform a
fresh permission check immediately before retrieving/streaming the
object. Do not create a public URL and assume the original check remains
valid.

Write a security design note tracing the exact request path for a
document download from router to policy service to storage adapter to
audit event.

## 6. Secure document storage and upload pipeline

Implement a private storage design:

-   Bucket/container is private; anonymous listing and reads are
    disabled.
-   Backend service credentials are the only credentials permitted to
    read/write objects.
-   Object keys are random, unguessable identifiers generated
    server-side. Do not use the original filename as the storage key.
-   Store original filename only as validated metadata, with output
    encoding on display.
-   Never expose internal bucket names, object keys, credentials or
    storage endpoints to the browser.
-   Do not use predictable sequential document IDs as access controls.
    UUIDs are useful identifiers but are not authorisation.
-   Encrypt data at rest. Use a documented envelope-encryption design
    where feasible: per-object data encryption key, authenticated
    encryption such as AES-256-GCM, and a separately protected
    key-encryption key. Keep master keys outside the database and object
    store. Include key versioning and rotation design. Do not invent a
    home-grown cryptographic algorithm.
-   Do not commit encryption keys. Provide a secure local
    key-generation/setup command and production secret injection
    instructions.
-   Explain backup and recovery of encryption keys. Losing the key must
    not be confused with deleting the file.
-   Stream files through the backend only after a fresh authorisation
    check.
-   Set safe `Content-Disposition` and `Content-Type`; default to
    attachment for risky/active formats.
-   Use `X-Content-Type-Options: nosniff`.
-   Do not render untrusted HTML, SVG or active content inline.
-   Use a separate, sandboxed preview strategy if previews are
    implemented. It is acceptable to defer previews and provide secure
    downloads instead.

Upload validation must include: - maximum size enforced at reverse proxy
and application layers; - extension allowlist; - MIME type inspection as
a hint only; - magic-byte/signature validation; - mismatch rejection; -
filename length and character restrictions; - path traversal and
null-byte handling; - double-extension and dangerous active-content
handling; - archive expansion limits / zip bombs if archives are
allowed; - malware scanning/quarantine workflow if ClamAV is enabled; -
per-user upload quotas/rate limits; - cleanup of partial uploads; -
audit event for accepted/rejected upload attempts without logging
document contents.

Do not trust `Content-Type` supplied by the browser. Test spoofed MIME
types, renamed executables, oversized files, malformed files and path
traversal filenames.

## 7. Audit trail --- evidence, not ordinary application logs

Audit events are a first-class security feature.

Record at least: - login success/failure and logout where available; -
document upload accepted/rejected; - document metadata changes; -
version uploads; - document preview/read/download success; - document
access denied; - grant creation, modification and revocation; - user
activation/deactivation and role changes; - document deletion,
restoration and retention actions; - admin security/configuration
actions; - AI recommendation generated, viewed, accepted, rejected or
modified.

Each event should include: - unique event ID; - UTC timestamp; - actor
user ID (or anonymous/unknown actor marker); - action and outcome; -
target type and target ID where safe; - request/correlation ID; - source
IP and user agent only as appropriate under the privacy policy; -
reason/context fields that do not contain secrets or document
contents; - previous event hash and current event hash.

Tamper-evidence: - Canonicalise the event payload deterministically. -
Compute a cryptographic hash over the canonical event plus previous
hash. - Serialize chain updates safely under concurrent requests
(transaction/locking or another defensible sequencing design). -
Restrict database privileges so the application role can insert audit
rows but cannot update/delete them, where practical. - Provide an audit
verification command/API that detects changed, deleted, reordered or
inserted events. - Periodically create signed checkpoints and export
them to a separately protected destination. Document what this protects
against and what it does not. - Do not claim hash chaining alone
prevents a database superuser from rewriting the entire chain. - If
external immutable/WORM storage is unavailable due the zero-cost
constraint, clearly document the residual risk and a reproducible
manual/offline checkpoint export. - Failed access attempts must be
recorded without disclosing document existence to the requester. -
Ensure audit failure behaviour is explicit. For high-risk actions such
as permission changes and downloads, prefer fail-closed if the audit
event cannot be durably recorded. Document the availability trade-off.

Create `docs/AUDIT_DESIGN.md` with the threat model, hash algorithm,
canonicalisation, concurrency strategy, verification procedure,
checkpoint process and limitations.

## 8. Search and metadata privacy

Implement search by: - document name; - owner; - category; -
created/modified date range.

Every query must be scoped to documents the caller is authorised to
discover. Do not return inaccessible document counts, names, owner
names, categories, snippets, thumbnails or existence signals. Search
must not become an IDOR side door.

Add pagination with stable ordering and safe limits. Validate filters
and sort fields against an allowlist. Avoid raw SQL concatenation. Test
that search, facets, counts and pagination never leak another user's
metadata.

## 9. Admin activity dashboard

Create an accessible, professional dashboard showing: - recent document
activity; - denied access attempts; - permission grants and
revocations; - unusual failed login/access patterns; - user account
changes; - audit-chain verification status; - quarantined/rejected
uploads.

Provide filters by time, actor, action, outcome and document ID where
the admin is allowed to see audit metadata. Redact secrets and sensitive
content. Add pagination and role enforcement. The admin must not be able
to use dashboard APIs to fetch document content.

## 10. Optional local AI feature --- never let AI grant access

Use Ollama only for an optional **access recommendation assistant**.

The assistant may recommend which named users might need access based on
owner-provided context and permitted metadata. It must never: - grant or
widen permissions; - change a grant; - bypass the authorisation
service; - make a final access decision; - receive confidential file
contents by default; - make network calls to an external model provider.

Required workflow: 1. Owner explicitly invokes recommendation. 2.
Backend sends only the minimum necessary metadata/context to the local
Ollama service. 3. Model output is treated as untrusted data and
validated against real users and allowed permission types. 4. Owner sees
the recommendation and must explicitly confirm or reject it. 5. Only the
normal permission service can apply a confirmed grant. 6. Audit the
request, model identifier, recommendation, owner decision and resulting
permission change. 7. If Ollama is offline, unavailable or returns
malformed output, all core TrustVault functions continue to work.

Use a configurable local model. Do not assume a model is installed.
Include setup instructions, model licence notes and a health check. Make
AI features clearly optional in the UI.

## 11. Frontend product experience

Build a polished, responsive, accessible enterprise application. Visual
quality matters, but security and correctness come first.

Pages: - Login - Dashboard with role-specific summaries - My Documents -
Shared With Me - Document details and permission panel - Upload
document - Search and filters - Document activity/history - User
administration (admin only) - Audit/security activity (admin only) -
Settings/profile - Not found / access denied / error states

UI requirements: - Clear role-aware navigation, but never treat hidden
controls as security. - Loading, empty, error, success and
permission-denied states. - Accessible labels, keyboard navigation,
focus states and contrast. - Confirmation for destructive actions and
permission revocation. - Show effective access and grant expiry
clearly. - Do not display secrets, storage object keys or internal
infrastructure details. - Avoid leaking inaccessible metadata in client
caches. Clear relevant cached data on logout, user switch and permission
changes. - Use consistent API error handling and correlation IDs for
support.

## 12. Database design and migrations

Design a normalised schema with constraints and indexes. At minimum
consider:

-   users (external identity subject, email, display name, role, active
    status, timestamps);
-   documents (UUID, owner, safe display name, category, description,
    lifecycle status, current version, timestamps);
-   document_versions (document, version number, object key, size,
    verified content type, checksum, encryption key version, scan
    status, creator, timestamp);
-   document_grants (document, grantee, permission, grantor, expiry,
    revoked timestamp, revocation reason);
-   audit_events (event data, sequence, previous hash, event hash);
-   audit_checkpoints (checkpoint metadata and signature);
-   categories or tags if required.

Use foreign keys, uniqueness constraints, check constraints and indexes.
Define deletion semantics and retention. Use Alembic migrations, not
manual schema changes as the only setup path. Add deterministic seed
data for demo accounts and documents. Seed passwords must be clearly
labelled demo-only and changed for any real deployment. Never use real
employee or salary data.

Define whether deletion is soft delete, retention tombstone or permanent
purge. Prefer a documented lifecycle with a recoverable soft-delete
period and a separate privileged purge process. Ensure deleted or
quarantined content cannot be downloaded.

## 13. API contract and endpoint authorisation

Create versioned REST APIs under `/api/v1`. Generate OpenAPI
documentation and maintain a human-readable `docs/API.md`.

For every endpoint document: - HTTP method and path; - purpose; -
required role; - resource-level permission; - request/response schema; -
expected status codes; - audit event produced; - whether the endpoint
can reveal resource existence.

Include endpoints for: - current user/profile; - document
upload/list/search/details/download; - metadata update/version upload; -
grants list/create/update/revoke; - delete/restore; - user
administration; - admin audit/activity; - audit verification/checkpoint
export; - AI recommendation and owner decision; - health/readiness.

Do not create an endpoint that returns a storage URL. Do not let the
client supply actor ID, owner ID, grantor ID or audit actor identity.
Derive actor identity from the validated server-side session/token.

## 14. Threat modelling --- comprehensive and honest

Create `THREATS.md` early, then update it as implementation and testing
reveal issues. Use a table with: - threat ID; - attack scenario; - asset
and trust boundary; - impact; - likelihood/severity; - mitigation
implemented; - exact test name(s); - residual risk / accepted risk; -
status.

Consider at least: - IDOR/BOLA by changing document IDs; - unauthorised
list/search/count/facet leakage; - direct object-storage access; -
guessed or leaked object keys; - stale/replayed download links; -
revocation race and time-of-check/time-of-use; - stale access/refresh
tokens after user deactivation; - privilege escalation via role or owner
fields in request bodies; - mass assignment; - grant manipulation and
self-grant; - admin implicit content access; - broken object-level
authorisation on every HTTP verb; - path traversal and filename
injection; - MIME spoofing, polyglot files, double extensions and active
content; - oversized uploads, decompression bombs and storage
exhaustion; - malware upload and scanner outage; - SQL injection and
unsafe sorting/filtering; - XSS through filenames, metadata or audit
fields; - CSRF where cookie-based auth is used; - CORS
misconfiguration; - JWT issuer/audience/signature/algorithm validation
errors; - weak password/session configuration and brute force; - account
enumeration; - rate-limit bypass; - secret/key exposure in logs, Git,
errors or browser; - encryption key loss, rotation failure and nonce
misuse; - audit event deletion/modification/reordering and concurrent
chain races; - audit failure during high-risk actions; - log injection
and forged client-supplied actor identity; - search and pagination side
channels; - cache leakage between users; - backup leakage and insecure
restore; - container privilege escalation, exposed Docker socket and
open internal ports; - dependency/supply-chain vulnerabilities; - SSRF
via URL import or preview (prefer not to implement URL import); -
malicious or prompt-injected AI output; - Ollama unavailable or exposed
publicly; - insecure deployment defaults, debug mode and default
credentials; - denial of service and resource exhaustion.

Do not write generic entries only. Each entry must connect to code and a
named test. Explicitly identify accepted risks.

## 15. Automated security tests --- make them capable of catching removed checks

Tests are a primary deliverable. Do not only test the happy path or
assert that the frontend hides a button.

Build integration tests with at least three distinct users: - Alice:
owner of document A; - Bob: viewer granted read access to document A but
no access to document B; - Carol: unrelated user with no access to
either document; - Admin: administrator who can see audit metadata but
cannot read document content by default.

Test all of these directly against HTTP endpoints:

### Isolation and IDOR

-   Bob cannot access Carol/Alice's unshared document by UUID.
-   Carol cannot access document metadata, content, download, version
    history, grants or audit details for an inaccessible document.
-   Changing IDs in URL, query, body, headers or nested request objects
    never changes the authenticated actor or owner.
-   User A cannot list or search another user's documents.
-   Counts, filters, pagination and category facets do not reveal
    inaccessible documents.

### Permission matrix

-   Owner can perform allowed owner actions.
-   Read grant allows reading/downloading only.
-   Read grant cannot edit metadata, upload versions, share or delete.
-   Edit grant has only the explicitly documented capabilities.
-   Revoked and expired grants fail immediately on the next request.
-   Inactive user with a valid old token is denied.
-   Admin cannot download content without a separate explicit grant.
-   One user cannot grant themselves or escalate their role.

### Download and storage

-   Direct MinIO anonymous read/list fails.
-   Object key alone is insufficient.
-   No API response exposes a permanent or long-lived storage URL.
-   Every download performs a fresh authorisation check.
-   A previously downloaded/issued link cannot be replayed after
    revocation. Prefer no issued link at all.
-   Quarantined, deleted and failed-scan documents cannot be downloaded.

### Upload

-   Reject invalid signature, MIME mismatch, dangerous extension, path
    traversal, oversized payload and malformed file.
-   Prevent filename XSS.
-   Handle interrupted upload without leaving accessible partial
    objects.
-   A user cannot upload on behalf of another owner by changing request
    fields.

### Audit

-   Success and denial produce correct audit records.
-   Permission grant/revoke includes actor, target, old/new permission
    and timestamp.
-   Audit verification detects modified, deleted, reordered and inserted
    events.
-   Concurrent event writes do not corrupt the chain.
-   Client cannot forge actor identity.
-   Secrets and document contents are not written into audit events.
-   If durable audit fails during a protected operation, behaviour
    matches the documented fail-closed policy.

### Mutation test / authorisation-check removal

Create a practical security regression procedure that demonstrates tests
fail if the central authorisation call is removed from a download or
metadata endpoint. Use mutation testing if feasible, or a documented
temporary mutation test script. Do not merely state that tests would
fail.

Run the full suite in CI. Make test failures block a successful build.

## 16. Deployment, live URL and operations

Provide a reproducible Docker Compose deployment containing the
frontend, API, PostgreSQL, Keycloak, MinIO, Caddy and optional
Ollama/ClamAV as appropriate.

Requirements: - Only public web ports exposed. - Internal services on a
private Docker network. - Persistent volumes for PostgreSQL, MinIO and
Keycloak. - Health checks and dependency readiness. - Non-root
containers where feasible. - Resource limits where supported. -
Production configuration separated from development configuration. - No
default production passwords. - HTTPS via Caddy when a valid domain is
configured. - Secure cookie, CORS, CSP, HSTS and other headers
appropriate to the chosen auth flow. - Database migrations run safely. -
Backups and restore instructions, including encryption key backup. -
Structured logs with secrets redacted. - Liveness and readiness
endpoints that reveal no sensitive configuration. - A deployment
smoke-test script.

Zero-cost hosting reality: - Do not assume a free PaaS provides
persistent disk, always-on compute, or a free managed database. -
Investigate current free options only when deployment is actually being
prepared; verify their limits and terms. - Keep the app deployable to a
single self-hosted Linux machine. - Provide a public demo option using a
free tunnel only if it can be configured safely. Explain that a
temporary tunnel URL may change and the host machine must remain
online. - A stable public URL may require a domain or a host with a
persistent public address; state any unavoidable cost/availability
constraint honestly. - Do not expose development services or the Docker
daemon through a tunnel. - Do not put demo credentials into a public
code repository beyond clearly labelled disposable seed credentials
intended for the judge demo. Force a password change if feasible.

Create: - `deployment/docker-compose.yml` - `deployment/Caddyfile` -
`.env.example` - `scripts/dev-up` - `scripts/dev-down` -
`scripts/healthcheck` - `scripts/backup` - `scripts/restore` (with
safety confirmation) - `scripts/deploy-smoke-test` -
`docs/DEPLOYMENT.md`

## 17. Git history and AI-use evidence

Create `PROMPTS.md` immediately. Maintain it throughout the project, not
at the end.

It must have at least five dated entries, with real dates and real
commit links once commits exist. Each entry must contain: - date; - tool
and task; - exact prompt or fair summary; - what the AI generated; -
what was specifically wrong, incomplete or risky; - what was changed
after human review; - test or inspection used to verify the
correction; - commit link/hash.

At least two entries must concern authorisation, access control or audit
integrity. Record genuine findings. Never fabricate mistakes, fixes,
test outcomes or commits. If an AI suggestion was correct, say what code
and tests were independently checked.

Add reusable Kiro steering/context files under `.kiro/steering/`: -
`product.md` - `architecture.md` - `security.md` - `testing.md` -
`coding-standards.md`

These should capture durable project rules, especially deny-by-default,
server-side checks, no direct object URLs, no implicit admin content
access, immediate revocation and audit integrity.

Use small, meaningful commits across the week. Do not create a fake
commit history or backdate commits.

## 18. Documentation and competition hand-in

Deliver: - `README.md` --- overview, features, architecture,
prerequisites, quick start, demo accounts, screenshots if real, security
warning for demo data. - `THREATS.md` --- detailed threat model,
mitigations, test mapping and accepted risks. - `PROMPTS.md` --- dated
AI usage log with honest corrections and commit links. -
`docs/ACCESS_CONTROL.md` --- role matrix and permission semantics. -
`docs/AUDIT_DESIGN.md` --- integrity model and limitations. -
`docs/API.md` --- endpoint-by-endpoint access policy. -
`docs/ARCHITECTURE.md` --- architecture and trust boundaries. -
`docs/DEPLOYMENT.md` --- clean-clone setup, production and public demo
deployment. - `docs/DATA_MODEL.md` --- schema and lifecycle. -
`docs/DEMO_SCRIPT.md` --- five-minute demo script with exact steps and
expected outcomes. - `docs/FINAL_WRITEUP.md` --- what was built,
permission model in plain language, what was deliberately not built, AI
use and mistakes caught, unfinished work and residual risks. - database
migrations and deterministic seed scripts. - automated tests and CI
configuration. - a real five-minute demo video only if recording
capability is available; otherwise provide the script and explicit
recording instructions. Never claim a video exists if it does not.

Demo accounts must cover Admin, Owner and Viewer. Provide disposable
credentials only in a local seed or deployment secret setup, never real
credentials. Explain how the judge can reset the demo data.

## 19. UI quality and demo readiness

The app should look like a polished enterprise security product: - calm,
professional visual language; - consistent spacing and typography; -
responsive layouts; - clear document status and access indicators; -
accessible tables and forms; - useful empty states; - no fake charts or
fabricated audit events; - admin dashboard data must come from actual
persisted audit events; - include a demo scenario that shows an allowed
user accessing a document and an unrelated user being denied.

Do not sacrifice security to make the demo look smooth.

## 20. Required build sequence

Execute in this order. Do not jump ahead and leave earlier phases
broken.

### Phase 0 --- repository inspection and design

-   Inspect workspace and available tools.
-   Write project plan, architecture diagram, ADRs, trust boundaries,
    role matrix and initial threat model.
-   Create `PROMPTS.md` and `.kiro/steering/` files.
-   Confirm chosen versions and licences.

### Phase 1 --- runnable foundation

-   Create frontend/backend projects.
-   Create Docker Compose with health checks and persistent volumes.
-   Add PostgreSQL migrations and Keycloak OIDC integration.
-   Add `/health/live` and `/health/ready`.
-   Add CI for lint/type-check/unit tests.
-   Verify clean-clone startup.

### Phase 2 --- identity and policy

-   Implement authenticated user resolution and active-account checks.
-   Implement roles, document ownership and document grants.
-   Implement the central authorisation policy service.
-   Write exhaustive policy unit tests before adding document endpoints.

### Phase 3 --- secure storage and documents

-   Implement private MinIO adapter.
-   Implement encryption and key handling.
-   Implement upload validation/quarantine.
-   Implement metadata, versions, download streaming and lifecycle.
-   Add integration tests for every route and direct storage access.

### Phase 4 --- grants, revocation and audit

-   Implement grants and revocation transactions.
-   Ensure next-request revocation semantics.
-   Implement audit events, hash chain, verification and checkpoints.
-   Add concurrency and tamper tests.

### Phase 5 --- search and admin

-   Implement access-filtered search.
-   Implement admin activity dashboard and filters.
-   Ensure admin sees audit metadata, not document contents by default.
-   Test for metadata leakage.

### Phase 6 --- AI and UI completion

-   Integrate optional local Ollama recommendations.
-   Require human approval and audit the full recommendation/decision.
-   Complete responsive frontend and all role-specific workflows.
-   Add browser end-to-end tests.

### Phase 7 --- adversarial testing and hardening

-   Review every route and every storage access path.
-   Run the complete threat checklist.
-   Run dependency and container scans where available.
-   Run mutation/removal test for central authorisation.
-   Fix findings and update `THREATS.md`.
-   Verify audit chain and backup/restore.

### Phase 8 --- deploy and hand in

-   Deploy early enough to test the real public URL.
-   Run smoke tests against the deployed system.
-   Confirm seed accounts work and judge workflow is understandable.
-   Complete all documentation.
-   Record the five-minute demo if recording tools are available.
-   Produce a final status report distinguishing complete, incomplete
    and accepted-risk items.

## 21. Definition of done

Do not declare TrustVault complete until all of the following are true:

-   A clean clone can be started using documented commands.
-   Authentication works for all three roles.
-   Every document operation is protected by server-side object-level
    authorisation.
-   Search and metadata are access-filtered.
-   Private object storage cannot be accessed anonymously.
-   Downloads are streamed only after a fresh permission check.
-   Revocation takes effect on the next request.
-   Audit records cover successful and denied activity.
-   Audit verification detects tampering.
-   Security integration tests cover the threat model.
-   The authorisation-removal/mutation test demonstrates that the tests
    catch a missing check.
-   Admin cannot read content just because of their role.
-   Upload validation and quarantine rules work.
-   Ollama is optional and does not affect core application
    availability.
-   The live deployment is tested, or the exact blocker is documented
    honestly.
-   `THREATS.md`, `PROMPTS.md`, API docs, deployment docs, demo script
    and final write-up are present and accurate.
-   No fake functionality, fake test results or invented deployment
    details remain.

## 22. Your first response and immediate next action

Do not generate the entire codebase in one response.

First: 1. Inspect the repository and runtime. 2. Produce a concise plan
with milestones. 3. Identify assumptions and any risks in the requested
stack. 4. Create Phase 0 files: architecture, threat model, role matrix,
Kiro steering files and `PROMPTS.md`. 5. Show the exact commands to run
and the files created. 6. Ask for approval only if an essential decision
cannot safely be made. Otherwise choose sensible secure defaults and
proceed.

Then implement one phase at a time, running tests and committing
meaningful changes. Prioritise a secure, demonstrable vertical slice
early: login → owner uploads a private document → grants read to a
viewer → viewer downloads through the API → owner revokes → viewer's
next download is denied and the denial is audited.

Remember: the goal is not to generate the most code. The goal is to
build a system that survives an adversarial judge, and to be able to
explain and defend every security decision.

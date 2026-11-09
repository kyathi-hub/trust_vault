# TrustVault — Demo Script (5 minutes)

This script demonstrates the core security value proposition:
**A user can only access documents they are explicitly authorised to access.**

---

## Setup (before demo)

```bash
bash scripts/dev-up.sh
bash scripts/healthcheck.sh
```

Open browser to `https://localhost`. Accept the self-signed certificate.

---

## Act 1 — Owner uploads and controls access (90 seconds)

**Log in as Alice** (Document Owner)
- Email: `alice@trustvault.local` / Password: `Alice1234!`
- If prompted to change password, set a new one and note it

**Show the dashboard** — Alice sees her documents, quick actions

**Upload a document**
1. Click "Upload Document"
2. Select any PDF or DOCX file
3. Name it "Q3 Financial Report"
4. Click Upload
5. Point out: "The file is encrypted at rest immediately. Scan status shows Pending or Clean."

**View the document detail page**
- Show the metadata, checksum, scan status
- Point out: "No storage URL is shown anywhere — direct object access is impossible"

**Grant Bob read access**
1. Click "Grant Access"
2. Select Bob (bob@trustvault.local)
3. Choose "Read" permission
4. Click Grant
5. Point out: "The grant is stored in the database. Bob's next request will be checked against it."

---

## Act 2 — Authorised access works (60 seconds)

**Log out, log in as Bob** (Viewer)
- Email: `bob@trustvault.local` / Password: `Bob12345!`

**Navigate to Shared With Me**
- The Q3 Financial Report appears

**Download the document**
- Click Download
- File downloads successfully
- Point out: "Every download triggers a fresh permission check AND writes an audit event"

---

## Act 3 — Unauthorised access is denied (60 seconds)

**Log out, log in as Carol** (Viewer with no access)
- Email: `carol@trustvault.local` / Password: `Carol123!`

**Navigate to My Documents**
- Empty — Carol sees nothing

**Try to access Alice's document directly**
- Copy the document URL from the previous session
- Paste it in Carol's browser
- Result: 404 Not Found
- Point out: "Not 403 — we don't even confirm the document exists to someone who has no access"

---

## Act 4 — Revocation is immediate (60 seconds)

**Log back in as Alice**

**Revoke Bob's access**
1. Navigate to the document
2. Click "Revoke" on Bob's grant
3. Confirm

**Log in as Bob immediately**
- Navigate to Shared With Me — the document is gone
- Try the direct URL — 404

**Point out**: "Bob's token is still valid — his JWT hasn't expired. But we check
the grant status on every request, not the token expiry. Revocation is immediate."

---

## Act 5 — Admin sees the evidence (30 seconds)

**Log in as Admin**
- Email: `admin@trustvault.local` / Password: `Admin1234!`

**Navigate to Audit Log**
- Show the chain of events: upload, grant, download, revocation, denied access
- Click "Verify Chain" — shows green "Chain integrity verified"
- Point out: "Admin can see all of this — but cannot download the document itself"

**Try to access the document as admin**
- Navigate to `/documents/{id}` — 404 Not Found
- "Admin is not a superuser for document content"

---

## Key Talking Points

1. **Deny by default** — nothing is accessible unless explicitly granted
2. **Server-side enforcement** — hiding a button is not security
3. **No storage URLs** — even a breach of the frontend reveals nothing
4. **Immediate revocation** — not "revoked when the token expires"
5. **Tamper-evident audit** — SHA-256 hash chain, verifiable
6. **Admin ≠ omniscience** — separation of privileges

---

## Resetting Demo Data

```bash
docker compose -f deployment/docker-compose.yml down -v
bash scripts/dev-up.sh
```

---
inclusion: always
---

# TrustVault — Product Context

TrustVault is a **secure document-sharing platform** built for a security engineering competition.

## Core Purpose
Multi-user platform for confidential company documents with strict per-document, per-user access control.

## Three Roles
- **Administrator**: Platform management, audit visibility. CANNOT read document contents.
- **Document Owner**: Uploads and manages their documents. Controls who has access.
- **Viewer**: Read-only (or edit if explicitly granted) access to specific documents.

## Key Product Rules
- A user must not gain document access by guessing an ID, changing a URL, calling API directly, replaying a token, or manipulating a request body.
- Every document operation must be authorized server-side.
- Every significant event must produce an immutable audit record.
- Admin is NOT a superuser for document content.

## Demo Accounts (Seed Data)
- `admin@trustvault.local` — Administrator role
- `alice@trustvault.local` — Document Owner (owns documents A, B)
- `bob@trustvault.local` — Viewer (granted read access to document A only)
- `carol@trustvault.local` — Viewer (no access to any document)

## What "Done" Means
- Clean clone starts with documented commands
- All three roles work end-to-end
- Revocation takes effect on next request
- Admin cannot read content
- Tests cover all threat scenarios

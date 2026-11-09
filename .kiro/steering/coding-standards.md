---
inclusion: always
---

# TrustVault — Coding Standards

## Python (Backend)

### Style & Tooling
- **ruff** for linting and formatting (replaces black + flake8 + isort)
- **mypy** in strict mode: `--strict` flag, no `# type: ignore` without explanation
- Python 3.12+ features allowed
- All functions have type annotations — no bare `Any` without justification

### FastAPI Patterns
```python
# Always use Annotated dependencies
from typing import Annotated
from fastapi import Depends

CurrentUser = Annotated[User, Depends(get_current_active_user)]

# Route handlers are thin — delegate to service layer
@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentResponse:
    return await document_service.get_document(db, current_user, document_id)
```

### Authorization Pattern
```python
# ALWAYS call this before any document operation
await authorize_document_action(
    db=db,
    actor=current_user,
    document_id=document_id,
    action=DocumentAction.CONTENT_READ,
)
# If unauthorized → raises HTTP 404 (not 403, to avoid existence disclosure)
# Audit the denial internally before raising
```

### Database Patterns
- Use SQLAlchemy 2.x async sessions
- All queries scoped to caller's accessible documents — never fetch-all-then-filter
- Use parameterized queries always — never string concatenation in SQL
- Transactions wrap permission check + mutation together (no TOCTOU)
- UTC timestamps everywhere: `datetime.now(UTC)` not `datetime.utcnow()`

### Error Handling
- Never expose internal error details to clients
- Log full error server-side with correlation ID
- Return generic error message to client
- `HTTPException(status_code=404)` for inaccessible resources (not 403)

### No TODOs in "complete" features
- Label deferred features explicitly: `# DEFERRED: feature X not implemented in v1`
- No placeholder handlers that return fake success
- No hard-coded success responses for security checks

## TypeScript (Frontend)

### Strict Mode
```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

### Security Rules
- Never store tokens in localStorage — use httpOnly cookies or memory only
- Never make authorization decisions in the frontend
- Never display raw error messages from the server (may leak info)
- Always encode user-supplied content before rendering (React does this by default — don't use `dangerouslySetInnerHTML`)
- Clear sensitive data from component state on logout

### API Client Pattern
```typescript
// Use TanStack Query for all server state
// Never cache document content across user sessions
// Clear query cache on logout and permission changes
queryClient.clear() // on logout
```

### Form Validation
- Zod schemas on the client for UX feedback
- Server validation is always authoritative
- Never disable server-side validation based on client result

## File & Secret Hygiene
- `.env` always in `.gitignore`
- No secrets, keys, or real credentials in source files
- No real personal data in seed scripts — use clearly labelled demo data
- `console.log` removed before commit (use structured logger)

## Commit Style
- Small, meaningful commits per feature/fix
- Format: `type(scope): description` — e.g., `feat(auth): add JWT validation middleware`
- Never commit with `--no-verify` unless documented
- No fake or backdated commits

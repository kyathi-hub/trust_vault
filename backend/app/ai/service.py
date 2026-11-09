"""
Optional AI recommendation service using local Ollama.

Security rules (non-negotiable):
1. Owner must explicitly invoke — never automatic.
2. Only document metadata is sent to Ollama — NEVER file contents.
3. Ollama output is untrusted data — validated before any use.
4. AI cannot grant, modify, or revoke permissions.
5. Owner must explicitly confirm before any grant is applied.
6. All AI interactions are fully audited.
7. If Ollama is unavailable, all core functions continue without it.
8. No external AI APIs — local Ollama only.
"""

import json
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)

# Maximum length of AI-generated text we'll process (prevent resource exhaustion)
MAX_RESPONSE_LENGTH = 4096


class OllamaUnavailableError(Exception):
    """Raised when Ollama is not available or not configured."""


async def get_access_recommendation(
    document_name: str,
    document_description: str,
    owner_context: str,
    available_users: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Ask local Ollama to suggest which users might need access to a document.

    Args:
        document_name: Safe display name of the document (not contents)
        document_description: Owner-provided description (not file contents)
        owner_context: Owner's explanation of why they want a recommendation
        available_users: List of {"id": ..., "display_name": ..., "email": ...} dicts
                         — no sensitive data beyond what owner already knows

    Returns:
        dict with "recommendations" list and "reasoning" string

    Raises:
        OllamaUnavailableError: If Ollama is disabled or unreachable
    """
    settings = get_settings()

    if not settings.ollama_enabled:
        raise OllamaUnavailableError("AI recommendations are not enabled")

    # Build a safe prompt — no document contents, no secrets
    user_list = "\n".join(
        f"- {u['display_name']} ({u['email']})" for u in available_users[:20]
    )
    prompt = f"""You are helping a document owner decide who might need access to a document.

Document name: {document_name}
Document description: {document_description}
Owner's context: {owner_context}

Available users:
{user_list}

Based ONLY on the document name, description, and context provided, suggest which users (if any) might need access.
Respond with valid JSON in this exact format:
{{
  "recommendations": [
    {{"email": "user@example.com", "permission": "read", "reason": "brief reason"}}
  ],
  "reasoning": "overall explanation"
}}

If you cannot make a recommendation, return {{"recommendations": [], "reasoning": "explanation"}}.
Do not invent users not in the list. Do not grant access — only suggest."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 512},
                },
            )
            resp.raise_for_status()
            raw_response = resp.json().get("response", "")
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise OllamaUnavailableError(f"Ollama not reachable: {exc}") from exc
    except Exception as exc:
        raise OllamaUnavailableError(f"Ollama error: {exc}") from exc

    # Parse and validate — treat AI output as untrusted
    return _parse_and_validate_response(raw_response, available_users)


def _parse_and_validate_response(
    raw: str,
    available_users: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Validate AI output against real users and allowed permissions.
    Rejects any recommendation for a user not in available_users.
    Rejects any permission not in {"read", "edit"}.
    """
    if len(raw) > MAX_RESPONSE_LENGTH:
        return {"recommendations": [], "reasoning": "AI response too long — discarded for safety"}

    # Extract JSON from response (model may include extra text)
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {"recommendations": [], "reasoning": "AI response was not valid JSON"}

    try:
        parsed = json.loads(raw[start:end])
    except json.JSONDecodeError:
        return {"recommendations": [], "reasoning": "AI response was not valid JSON"}

    if not isinstance(parsed, dict):
        return {"recommendations": [], "reasoning": "Invalid AI response structure"}

    # Validate each recommendation against actual user list
    valid_emails = {u["email"] for u in available_users}
    allowed_permissions = {"read", "edit"}

    validated_recs = []
    for rec in parsed.get("recommendations", [])[:10]:  # cap at 10
        if not isinstance(rec, dict):
            continue
        email = str(rec.get("email", "")).strip().lower()
        permission = str(rec.get("permission", "read")).strip().lower()
        reason = str(rec.get("reason", ""))[:500]  # cap reason length

        # Only include users that actually exist in the system
        if email not in valid_emails:
            logger.warning("ai_recommendation_unknown_user", email=email)
            continue
        if permission not in allowed_permissions:
            permission = "read"  # safe default

        # Find the user ID for this email
        user = next((u for u in available_users if u["email"] == email), None)
        if user:
            validated_recs.append({
                "user_id": user["id"],
                "email": email,
                "display_name": user.get("display_name", ""),
                "permission": permission,
                "reason": reason,
            })

    reasoning = str(parsed.get("reasoning", ""))[:1000]

    return {
        "recommendations": validated_recs,
        "reasoning": reasoning,
        "model_used": get_settings().ollama_model,
    }


async def check_ollama_health() -> bool:
    """Check if Ollama is available."""
    settings = get_settings()
    if not settings.ollama_enabled:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False

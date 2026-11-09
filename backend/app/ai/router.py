"""
AI recommendation router — optional Ollama-powered access suggestions.

Security properties:
- Owner must explicitly invoke
- Only metadata sent to Ollama — never file contents
- Recommendations are suggestions only — owner must confirm
- Only the normal permissions service applies actual grants
- Full audit trail of request, recommendation, and owner decision
- If Ollama unavailable, returns 503 — core app unaffected
"""
import uuid

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.service import OllamaUnavailableError, check_ollama_health, get_access_recommendation
from app.audit.service import record_event
from app.auth.dependencies import CurrentUser
from app.config import get_settings
from app.database import DbSession
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.permissions.actions import DocumentAction
from app.permissions.service import authorize_document_action

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/documents/{document_id}/ai", tags=["ai"])


class AIRecommendationRequest(BaseModel):
    context: str = ""  # Owner's explanation — max 500 chars


class AIRecommendationResponse(BaseModel):
    recommendations: list[dict]
    reasoning: str
    model_used: str
    warning: str = "These are suggestions only. You must review and confirm before any access is granted."


@router.post("/recommend", response_model=AIRecommendationResponse, summary="Get AI access recommendation (owner only)")
async def get_recommendation(
    document_id: uuid.UUID,
    body: AIRecommendationRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> AIRecommendationResponse:
    """
    Ask local Ollama to suggest who might need access to this document.
    Only sends document name, description, and owner context — never file contents.
    Owner must confirm before any grant is applied via the grants endpoint.
    """
    settings = get_settings()
    if not settings.ollama_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI recommendations are not enabled on this server",
        )

    # Only owner can invoke AI recommendations
    doc = await authorize_document_action(
        db, current_user, document_id, DocumentAction.GRANT_LIST,
        correlation_id=request.headers.get("X-Correlation-ID"),
    )

    # Fetch active users for recommendation (names/emails only — no sensitive data)
    result = await db.execute(
        select(User).where(User.is_active == True, User.id != current_user.id)  # noqa: E712
    )
    available_users = [
        {"id": str(u.id), "email": u.email, "display_name": u.display_name}
        for u in result.scalars().all()
    ]

    try:
        recommendation = await get_access_recommendation(
            document_name=doc.display_name,
            document_description=doc.description,
            owner_context=body.context[:500],
            available_users=available_users,
        )
    except OllamaUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is currently unavailable. Try again later.",
        ) from exc

    # Audit the AI request and result
    await record_event(
        db=db,
        actor=current_user,
        action="ai:recommendation_generated",
        outcome="success",
        target_type="document",
        target_id=str(document_id),
        metadata={
            "model": recommendation.get("model_used"),
            "recommendation_count": len(recommendation.get("recommendations", [])),
            # Do NOT log the recommendations themselves — they contain user IDs
            # Do NOT log document contents
        },
        correlation_id=request.headers.get("X-Correlation-ID"),
    )

    return AIRecommendationResponse(
        recommendations=recommendation.get("recommendations", []),
        reasoning=recommendation.get("reasoning", ""),
        model_used=recommendation.get("model_used", settings.ollama_model),
    )


@router.get("/health", summary="Check AI service availability")
async def ai_health(current_user: CurrentUser) -> dict:
    """Returns whether Ollama is available. Does not require admin."""
    available = await check_ollama_health()
    return {"available": available, "enabled": get_settings().ollama_enabled}

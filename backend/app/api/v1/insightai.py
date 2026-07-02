import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai_engine.registry import list_providers
from app.ai_engine.service import generate_insights, list_insights
from app.auth.dependencies import require_role
from app.collectors.job_service import get_audit_job
from app.database.session import get_db
from app.models.role import ADMIN, AUDITOR, VIEWER
from app.models.user import User
from app.schemas.insightai import AIInsightResponse, InsightGenerateRequest, ProviderStatus

router = APIRouter(prefix="/insightai", tags=["InsightAI"])


@router.post("/jobs/{job_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate(
    job_id: uuid.UUID,
    payload: InsightGenerateRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR)),
) -> dict:
    if get_audit_job(db, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        await generate_insights(db, job_id, payload.provider, payload.insight_types)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return {"status": "analyzing"}


@router.get("/jobs/{job_id}/insights", response_model=list[AIInsightResponse])
def get_insights(
    job_id: uuid.UUID,
    insight_type: str | None = None,
    finding_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR, VIEWER)),
) -> list[AIInsightResponse]:
    if get_audit_job(db, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return list_insights(db, job_id, insight_type, finding_id)


@router.get("/providers", response_model=list[ProviderStatus])
def get_providers(
    _current_user: User = Depends(require_role(ADMIN)),
) -> list[ProviderStatus]:
    return list_providers()

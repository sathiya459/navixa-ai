import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.job_service import get_audit_job
from app.database.session import get_db
from app.hub_spoke_validator.service import list_findings, run_ai_validation, run_validation
from app.models.role import ADMIN, READER
from app.models.user import User
from app.schemas.validate import FindingResponse, ValidateRunRequest

router = APIRouter(prefix="/validate", tags=["Validate"])


@router.post("/jobs/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_validate(
    job_id: uuid.UUID,
    payload: ValidateRunRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> dict:
    audit_job = get_audit_job(db, job_id)
    if audit_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if payload.analysis_mode == "ai":
        try:
            await run_ai_validation(db, audit_job, payload.hub_ids, payload.provider)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    else:
        run_validation(db, audit_job, payload.hub_ids)

    return {"status": audit_job.status, "analysis_mode": payload.analysis_mode}


@router.get("/jobs/{job_id}/results", response_model=list[FindingResponse])
def get_validate_results(
    job_id: uuid.UUID,
    severity: str | None = None,
    finding_type: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> list[FindingResponse]:
    audit_job = get_audit_job(db, job_id)
    if audit_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return list_findings(db, job_id, severity, finding_type)

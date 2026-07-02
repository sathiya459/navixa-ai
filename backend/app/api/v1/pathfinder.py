import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.job_service import get_audit_job
from app.database.session import get_db
from app.internet_path_engine.service import list_pathfinder_findings, run_pathfinder
from app.models.role import ADMIN, AUDITOR, VIEWER
from app.models.user import User
from app.schemas.pathfinder import PathfinderRunRequest
from app.schemas.validate import FindingResponse

router = APIRouter(prefix="/pathfinder", tags=["Pathfinder"])


@router.post("/jobs/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
def run_pathfinder_job(
    job_id: uuid.UUID,
    payload: PathfinderRunRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR)),
) -> dict:
    audit_job = get_audit_job(db, job_id)
    if audit_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    run_pathfinder(db, audit_job, payload.direction)
    return {"status": audit_job.status}


@router.get("/jobs/{job_id}/results", response_model=list[FindingResponse])
def get_pathfinder_results(
    job_id: uuid.UUID,
    finding_type: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR, VIEWER)),
) -> list[FindingResponse]:
    if get_audit_job(db, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return list_pathfinder_findings(db, job_id, finding_type)

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.job_service import get_audit_job
from app.database.session import get_db
from app.graph_engine.topology_service import get_job_topology
from app.models.role import ADMIN, READER
from app.models.user import User
from app.schemas.graph import TopologyResponse

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/jobs/{job_id}/topology", response_model=TopologyResponse)
def get_topology(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> TopologyResponse:
    if get_audit_job(db, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return get_job_topology(db, job_id)

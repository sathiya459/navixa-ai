import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.job_service import get_audit_job
from app.database.session import get_db
from app.models.role import ADMIN, READER
from app.models.user import User
from app.schemas.watch import (
    ResourceChangeResponse,
    ScheduledDiscoveryCreate,
    ScheduledDiscoveryResponse,
)
from app.watch.service import (
    create_scheduled_discovery,
    delete_scheduled_discovery,
    list_changes,
    list_scheduled_discoveries,
    run_change_detection,
)

router = APIRouter(prefix="/watch", tags=["Watch"])


@router.post(
    "/schedules", response_model=ScheduledDiscoveryResponse, status_code=status.HTTP_201_CREATED
)
def create_schedule(
    payload: ScheduledDiscoveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> ScheduledDiscoveryResponse:
    return create_scheduled_discovery(
        db,
        payload.tenant_id,
        payload.scope_ids,
        payload.interval_minutes,
        payload.hub_selection,
        created_by=current_user.id,
    )


@router.get("/schedules", response_model=list[ScheduledDiscoveryResponse])
def list_schedules(
    tenant_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> list[ScheduledDiscoveryResponse]:
    return list_scheduled_discoveries(db, tenant_id)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> None:
    if not delete_scheduled_discovery(db, schedule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")


@router.post("/jobs/{job_id}/diff", response_model=list[ResourceChangeResponse])
def diff_job(
    job_id: uuid.UUID,
    compare_to: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> list[ResourceChangeResponse]:
    if get_audit_job(db, job_id) is None or get_audit_job(db, compare_to) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return run_change_detection(db, job_id, compare_to)


@router.get("/jobs/{job_id}/changes", response_model=list[ResourceChangeResponse])
def get_changes(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> list[ResourceChangeResponse]:
    if get_audit_job(db, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return list_changes(db, job_id)

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.job_service import (
    create_audit_job,
    delete_audit_job,
    get_audit_job,
    list_audit_jobs,
)
from app.database.session import get_db
from app.models.audit_job import AuditJobScope, ResourceCollectionStatusRow
from app.models.network_resource import NetworkResource
from app.models.role import ADMIN, AUDITOR, VIEWER
from app.models.user import User
from app.schemas.discover import (
    AuditJobCreate,
    AuditJobListItem,
    AuditJobResponse,
    JobStatusResponse,
    NetworkResourceResponse,
    ResourceStatusResponse,
    ScopeStatusResponse,
)
from app.workers.tasks import run_discovery

router = APIRouter(prefix="/discover", tags=["Discover"])


@router.post("/jobs", response_model=AuditJobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: AuditJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN, AUDITOR)),
) -> AuditJobResponse:
    audit_job = create_audit_job(db, payload, initiated_by=current_user.id)
    run_discovery.delay(str(audit_job.id))
    return audit_job


@router.get("/jobs", response_model=list[AuditJobListItem])
def list_jobs(
    tenant_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR, VIEWER)),
) -> list[AuditJobListItem]:
    return list_audit_jobs(db, tenant_id)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> None:
    audit_job = get_audit_job(db, job_id)
    if audit_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    delete_audit_job(db, audit_job)


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR, VIEWER)),
) -> JobStatusResponse:
    audit_job = get_audit_job(db, job_id)
    if audit_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job_scopes = db.query(AuditJobScope).filter(AuditJobScope.audit_job_id == job_id).all()
    scope_statuses = []
    for job_scope in job_scopes:
        resource_rows = (
            db.query(ResourceCollectionStatusRow)
            .filter(ResourceCollectionStatusRow.audit_job_scope_id == job_scope.id)
            .all()
        )
        scope_statuses.append(
            ScopeStatusResponse(
                scope_id=job_scope.cloud_scope_id,
                status=job_scope.status,
                resource_statuses=[
                    ResourceStatusResponse.model_validate(r) for r in resource_rows
                ],
            )
        )

    return JobStatusResponse(status=audit_job.status, scopes=scope_statuses)


@router.get("/jobs/{job_id}/resources", response_model=list[NetworkResourceResponse])
def get_job_resources(
    job_id: uuid.UUID,
    resource_type: str | None = None,
    scope_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, AUDITOR, VIEWER)),
) -> list[NetworkResourceResponse]:
    audit_job = get_audit_job(db, job_id)
    if audit_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    query = (
        db.query(NetworkResource)
        .join(AuditJobScope, NetworkResource.audit_job_scope_id == AuditJobScope.id)
        .filter(AuditJobScope.audit_job_id == job_id)
    )
    if resource_type:
        query = query.filter(NetworkResource.resource_type == resource_type)
    if scope_id:
        query = query.filter(AuditJobScope.cloud_scope_id == scope_id)

    return query.all()

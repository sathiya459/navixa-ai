import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.job_service import get_audit_job
from app.database.session import get_db
from app.models.role import ADMIN, READER
from app.models.user import User
from app.reports.inventory import list_discovered_resources, resources_to_csv
from app.reports.service import generate_report, get_report, list_reports_for_job
from app.schemas.reports import DiscoveredResourceResponse, ReportGenerateRequest, ReportResponse

router = APIRouter(prefix="/reports", tags=["Reports"])

_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "html": "text/html",
}


@router.post(
    "/jobs/{job_id}/generate", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED
)
def create_report(
    job_id: uuid.UUID,
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> ReportResponse:
    audit_job = get_audit_job(db, job_id)
    if audit_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return generate_report(db, audit_job, payload.report_type, payload.format, current_user.id)


def _parse_optional_uuid(value: str | None) -> uuid.UUID | None:
    """Query params arrive as strings - an empty string (e.g. a frontend
    filter reset to "", or a hand-built URL) should mean "no filter", not a
    422, since `uuid.UUID | None` FastAPI param typing would otherwise
    reject `""` as an invalid UUID rather than treating it like an absent
    param."""
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid UUID: {value}"
        ) from None


@router.get("/resources", response_model=list[DiscoveredResourceResponse])
def get_discovered_resources(
    provider: str | None = None,
    tenant_id: str | None = None,
    scope_id: str | None = None,
    resource_type: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> list[DiscoveredResourceResponse]:
    """Current discovered inventory across all tenants, for the Reports
    page's browse/filter view - each cloud scope's most recently
    discovered generation of resources, not the full historical record
    across every past Discover run (see `reports/inventory.py`)."""
    return list_discovered_resources(
        db,
        provider or None,
        _parse_optional_uuid(tenant_id),
        _parse_optional_uuid(scope_id),
        resource_type or None,
    )


@router.get("/resources/export")
def export_discovered_resources(
    provider: str | None = None,
    tenant_id: str | None = None,
    scope_id: str | None = None,
    resource_type: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> Response:
    resources = list_discovered_resources(
        db,
        provider or None,
        _parse_optional_uuid(tenant_id),
        _parse_optional_uuid(scope_id),
        resource_type or None,
    )
    csv_content = resources_to_csv(resources)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="navixa-discovered-resources.csv"'},
    )


@router.get("/{report_id}", response_model=ReportResponse)
def read_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> ReportResponse:
    report = get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.get("/{report_id}/download")
def download_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> FileResponse:
    report = get_report(db, report_id)
    if report is None or report.file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return FileResponse(
        report.file_path,
        media_type=_MEDIA_TYPES[report.format],
        filename=f"navixa-{report.report_type}-report.{report.file_path.rsplit('.', 1)[-1]}",
    )


@router.get("/jobs/{job_id}", response_model=list[ReportResponse])
def list_job_reports(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> list[ReportResponse]:
    if get_audit_job(db, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return list_reports_for_job(db, job_id)

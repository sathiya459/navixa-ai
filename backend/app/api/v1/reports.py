import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.job_service import get_audit_job
from app.database.session import get_db
from app.models.role import ADMIN, READER
from app.models.user import User
from app.reports.service import generate_report, get_report, list_reports_for_job
from app.schemas.reports import ReportGenerateRequest, ReportResponse

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

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.audit_job import AuditJob
from app.models.report import Report
from app.reports.context import build_report_context
from app.reports.renderers.excel_renderer import render_excel
from app.reports.renderers.html_renderer import render_html
from app.reports.renderers.pdf_renderer import render_pdf

settings = get_settings()

_EXTENSIONS = {"pdf": "pdf", "excel": "xlsx", "html": "html"}


def generate_report(
    db: Session, audit_job: AuditJob, report_type: str, report_format: str, generated_by: uuid.UUID
) -> Report:
    report = Report(
        audit_job_id=audit_job.id,
        report_type=report_type,
        format=report_format,
        status="queued",
        generated_by=generated_by,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    try:
        context = build_report_context(db, audit_job)

        if report_format == "pdf":
            content: bytes = render_pdf(context, report_type)
        elif report_format == "excel":
            content = render_excel(context, report_type)
        elif report_format == "html":
            content = render_html(context, report_type).encode("utf-8")
        else:
            raise ValueError(f"Unsupported report format: {report_format}")

        reports_dir = Path(settings.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        file_path = reports_dir / f"{report.id}.{_EXTENSIONS[report_format]}"
        file_path.write_bytes(content)

        report.file_path = str(file_path)
        report.status = "completed"
    except Exception:  # noqa: BLE001
        report.status = "failed"
        raise
    finally:
        db.commit()
        db.refresh(report)

    return report


def get_report(db: Session, report_id: uuid.UUID) -> Report | None:
    return db.get(Report, report_id)


def list_reports_for_job(db: Session, audit_job_id: uuid.UUID) -> list[Report]:
    return db.query(Report).filter(Report.audit_job_id == audit_job_id).all()

"""PDF rendering via fpdf2 (pure Python, no native/system dependencies -
unlike WeasyPrint, which needs Cairo/Pango and is painful to install
reliably across platforms). Layout is built directly rather than from the
HTML template, since fpdf2 doesn't render arbitrary HTML/CSS.
"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.reports.context import ReportContext

SEVERITY_COLORS = {
    "critical": (183, 28, 28),
    "high": (211, 47, 47),
    "medium": (245, 124, 0),
    "low": (56, 142, 60),
    "informational": (85, 85, 85),
}


def _line(pdf: FPDF, height: float, text: str) -> None:
    pdf.cell(0, height, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def render_pdf(context: ReportContext, report_type: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(11, 61, 145)
    _line(pdf, 12, f"NAVIXA AI - {report_type.capitalize()} Report")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(85, 85, 85)
    _line(pdf, 6, f"Tenant: {context.tenant_name} ({context.provider.upper()})")
    _line(pdf, 6, f"Audit Job: {context.audit_job_id}")
    _line(pdf, 6, f"Status: {context.job_status}")
    _line(pdf, 6, f"Audit Created: {context.created_at}")
    pdf.ln(4)

    if context.exec_summary:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(0, 0, 0)
        _line(pdf, 8, "Executive Summary")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, context.exec_summary)
        pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(0, 0, 0)
    _line(pdf, 8, "Findings Summary")
    pdf.set_font("Helvetica", "", 10)
    if context.severity_counts:
        for severity, count in context.severity_counts.items():
            color = SEVERITY_COLORS.get(severity, (0, 0, 0))
            pdf.set_text_color(*color)
            _line(pdf, 6, f"{severity.capitalize()}: {count}")
    else:
        pdf.set_text_color(0, 0, 0)
        _line(pdf, 6, "No findings identified.")
    pdf.ln(2)

    if report_type != "executive" and context.findings:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(0, 0, 0)
        _line(pdf, 8, "Detailed Findings")
        pdf.set_font("Helvetica", "", 9)
        for finding in context.findings:
            color = SEVERITY_COLORS.get(finding["severity"], (0, 0, 0))
            pdf.set_text_color(*color)
            pdf.multi_cell(
                0,
                5,
                f"[{finding['severity'].upper()}] {finding['finding_type']}: {finding['title']}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 5, finding["description"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)

    return bytes(pdf.output())

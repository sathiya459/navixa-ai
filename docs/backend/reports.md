# reports

Report generation in PDF, Excel, and HTML formats.

## Files

- `context.py` — builds a report data context from an audit job.
- `service.py` — `generate_report`: creates a `Report` row and renders it via the requested format.
- `renderers/pdf_renderer.py` — fpdf2-based PDF rendering.
- `renderers/excel_renderer.py` — openpyxl-based Excel rendering.
- `renderers/html_renderer.py` — jinja2-based HTML rendering.

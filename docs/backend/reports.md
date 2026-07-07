# reports

Report generation in PDF, Excel, and HTML formats, plus the cross-job
discovered-resource inventory backing the frontend's Reports page.

## Files

- `context.py` — builds a report data context from an audit job.
- `service.py` — `generate_report`: creates a `Report` row and renders it via the requested format.
- `renderers/pdf_renderer.py` — fpdf2-based PDF rendering.
- `renderers/excel_renderer.py` — openpyxl-based Excel rendering.
- `renderers/html_renderer.py` — jinja2-based HTML rendering.
- `inventory.py` — `list_discovered_resources()`/`resources_to_csv()`: "what has NAVIXA Discover found so far", independent of any single audit job, filterable by provider/tenant/cloud scope (subscription/account/project/compartment). Each Discover run creates fresh `NetworkResource` rows rather than updating previous ones in place, so "current inventory" is defined as each cloud scope's *most recently created* audit job's resources only - re-running Discover naturally supersedes stale rows in this view without deleting the historical record other pages still rely on. Backed by `GET /api/v1/reports/resources` (JSON) and `GET /api/v1/reports/resources/export` (CSV download) - both registered before the `/{report_id}` catch-all route in `api/v1/reports.py`, since FastAPI matches path routes in registration order.

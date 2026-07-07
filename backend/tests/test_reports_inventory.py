import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.v1.reports import _parse_optional_uuid
from app.main import app
from app.reports.inventory import resources_to_csv
from app.schemas.reports import DiscoveredResourceResponse


def _resource(**overrides) -> DiscoveredResourceResponse:
    defaults = dict(
        id=uuid.uuid4(),
        provider="azure",
        resource_type="network",
        native_id="vnet-hub-dev",
        name="vnet-hub-dev",
        attributes={"foo": "bar"},
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        audit_job_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        tenant_name="Acme Corp",
        scope_id=uuid.uuid4(),
        scope_type="subscription",
        scope_display_name="prod-subscription",
    )
    defaults.update(overrides)
    return DiscoveredResourceResponse(**defaults)


def test_resources_to_csv_includes_header_and_rows():
    csv_text = resources_to_csv([_resource(), _resource(native_id="vnet-spoke1-dev")])
    lines = csv_text.strip().splitlines()
    assert lines[0] == "provider,resource_type,native_id,name,tenant_name,scope_type,scope_display_name,collected_at"
    assert len(lines) == 3
    assert "vnet-hub-dev" in lines[1]
    assert "vnet-spoke1-dev" in lines[2]


def test_resources_to_csv_omits_raw_attributes_column():
    csv_text = resources_to_csv([_resource(attributes={"secret": "should-not-leak"})])
    assert "should-not-leak" not in csv_text


def test_resources_to_csv_handles_empty_list():
    csv_text = resources_to_csv([])
    assert csv_text.strip() == (
        "provider,resource_type,native_id,name,tenant_name,scope_type,scope_display_name,collected_at"
    )


def test_resources_route_is_not_shadowed_by_report_id_route():
    """GET /reports/{report_id} is a UUID path param registered in the same
    router - if /reports/resources were declared after it (as it originally
    was), FastAPI would match "resources" as report_id first and this call
    would 422 on UUID parsing instead of reaching get_discovered_resources.
    An unauthenticated 401/403 (not 422) proves the route resolved
    correctly."""
    client = TestClient(app)
    response = client.get("/api/v1/reports/resources")
    assert response.status_code in (401, 403)

    response = client.get("/api/v1/reports/resources/export")
    assert response.status_code in (401, 403)


def test_parse_optional_uuid_treats_empty_string_as_none():
    """A frontend filter reset to "" (rather than omitted entirely) must
    not 422 - this was the actual bug reported: the Reports page's
    "All tenants"/"All scopes" filter options set the query param to "",
    and `uuid.UUID | None`-typed FastAPI params reject "" outright."""
    assert _parse_optional_uuid("") is None
    assert _parse_optional_uuid(None) is None


def test_parse_optional_uuid_parses_valid_uuid():
    value = uuid.uuid4()
    assert _parse_optional_uuid(str(value)) == value


def test_parse_optional_uuid_rejects_malformed_uuid():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _parse_optional_uuid("not-a-uuid")
    assert exc_info.value.status_code == 422

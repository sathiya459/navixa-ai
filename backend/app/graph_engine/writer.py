"""Converts `NetworkResource` ORM rows into the plain dataclass shape that
`topology_service.py` and the deviation-detection modules build on.
"""

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class GraphResourceInput:
    id: uuid.UUID
    resource_type: str
    provider: str
    native_id: str
    name: str | None
    attributes: dict[str, Any]


def resources_to_graph_inputs(resources: list[Any]) -> list[GraphResourceInput]:
    """Shared by the topology service and anything else that needs the
    normalized Postgres inventory in this shape, so both build from the
    exact same conversion.
    """
    return [
        GraphResourceInput(
            id=r.id,
            resource_type=r.resource_type,
            provider=r.provider,
            native_id=r.native_id,
            name=r.name,
            attributes=r.attributes,
        )
        for r in resources
    ]

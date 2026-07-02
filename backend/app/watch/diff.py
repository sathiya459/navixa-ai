"""Pure diff logic for NAVIXA Watch change detection (Section 2).

Kept dependency-free (no DB/ORM types) so it's trivially unit-testable;
the service layer adapts NetworkResource rows into the plain dicts this
expects.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ResourceSnapshot:
    resource_type: str
    native_id: str
    attributes: dict[str, Any]


@dataclass
class ResourceDiffEntry:
    resource_type: str
    native_id: str
    change_type: str  # "added" | "removed" | "modified"
    previous_attributes: dict[str, Any] | None
    current_attributes: dict[str, Any] | None


def compute_resource_diff(
    previous: list[ResourceSnapshot], current: list[ResourceSnapshot]
) -> list[ResourceDiffEntry]:
    previous_by_key = {(r.resource_type, r.native_id): r for r in previous}
    current_by_key = {(r.resource_type, r.native_id): r for r in current}

    diff: list[ResourceDiffEntry] = []

    for key, resource in current_by_key.items():
        if key not in previous_by_key:
            diff.append(
                ResourceDiffEntry(
                    resource_type=resource.resource_type,
                    native_id=resource.native_id,
                    change_type="added",
                    previous_attributes=None,
                    current_attributes=resource.attributes,
                )
            )

    for key, resource in previous_by_key.items():
        if key not in current_by_key:
            diff.append(
                ResourceDiffEntry(
                    resource_type=resource.resource_type,
                    native_id=resource.native_id,
                    change_type="removed",
                    previous_attributes=resource.attributes,
                    current_attributes=None,
                )
            )

    for key in set(previous_by_key) & set(current_by_key):
        previous_resource = previous_by_key[key]
        current_resource = current_by_key[key]
        if previous_resource.attributes != current_resource.attributes:
            diff.append(
                ResourceDiffEntry(
                    resource_type=current_resource.resource_type,
                    native_id=current_resource.native_id,
                    change_type="modified",
                    previous_attributes=previous_resource.attributes,
                    current_attributes=current_resource.attributes,
                )
            )

    return diff

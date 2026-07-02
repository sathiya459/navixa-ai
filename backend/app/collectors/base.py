from dataclasses import dataclass, field
from typing import Any, Literal

CollectionStatus = Literal["success", "partial", "failed"]


@dataclass
class CollectionResult:
    resource_type: str
    status: CollectionStatus
    items: list[dict[str, Any]] = field(default_factory=list)
    error_detail: str | None = None
    duration_ms: int = 0

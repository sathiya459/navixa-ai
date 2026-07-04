import asyncio
from collections.abc import Awaitable, Callable
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


async def run_collectors_with_progress(
    collectors: dict[str, Awaitable[CollectionResult]],
    on_result: Callable[[CollectionResult], Awaitable[None]] | None = None,
) -> list[CollectionResult]:
    """Runs one coroutine per resource type concurrently, reporting each
    result to `on_result` (if given) as soon as it completes rather than
    waiting for every resource type to finish - this is what lets NAVIXA
    Discover surface live "N of M resource types collected" progress
    instead of the whole scope appearing stuck until it's entirely done.

    Each collector's own exception is caught here (keyed by its known
    resource_type) rather than relying on `asyncio.gather`'s
    `return_exceptions=True`, so a failure still reports a proper
    resource_type instead of "unknown".
    """

    async def _wrap(resource_type: str, coro: Awaitable[CollectionResult]) -> CollectionResult:
        try:
            result = await coro
        except Exception as exc:  # noqa: BLE001
            result = CollectionResult(resource_type=resource_type, status="failed", error_detail=str(exc))
        if on_result is not None:
            await on_result(result)
        return result

    return await asyncio.gather(*(_wrap(rt, coro) for rt, coro in collectors.items()))

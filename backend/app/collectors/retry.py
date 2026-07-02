import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from botocore.exceptions import ClientError

T = TypeVar("T")

THROTTLE_ERROR_CODES = {"Throttling", "ThrottlingException", "TooManyRequestsException", "RequestLimitExceeded"}


async def with_retry(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
) -> T:
    """Exponential backoff + jitter retry for throttled cloud API calls."""
    attempt = 0
    while True:
        try:
            return await func()
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            attempt += 1
            if error_code not in THROTTLE_ERROR_CODES or attempt >= max_attempts:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            await asyncio.sleep(delay + random.uniform(0, delay * 0.1))

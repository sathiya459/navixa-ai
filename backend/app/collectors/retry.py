import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

AWS_THROTTLE_ERROR_CODES = {
    "Throttling",
    "ThrottlingException",
    "TooManyRequestsException",
    "RequestLimitExceeded",
}


async def with_retry(
    func: Callable[[], Awaitable[T]],
    is_throttled: Callable[[Exception], bool],
    max_attempts: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
) -> T:
    """Generic exponential backoff + jitter retry for throttled cloud API calls.

    `is_throttled` classifies whether a caught exception represents a
    provider throttling response; anything else is re-raised immediately.
    """
    attempt = 0
    while True:
        try:
            return await func()
        except Exception as exc:  # noqa: BLE001
            attempt += 1
            if not is_throttled(exc) or attempt >= max_attempts:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            await asyncio.sleep(delay + random.uniform(0, delay * 0.1))


def is_aws_throttled(exc: Exception) -> bool:
    from botocore.exceptions import ClientError

    if not isinstance(exc, ClientError):
        return False
    return exc.response.get("Error", {}).get("Code", "") in AWS_THROTTLE_ERROR_CODES


def is_azure_throttled(exc: Exception) -> bool:
    from azure.core.exceptions import HttpResponseError

    if not isinstance(exc, HttpResponseError):
        return False
    return exc.status_code == 429


def is_gcp_throttled(exc: Exception) -> bool:
    from google.api_core.exceptions import ResourceExhausted, TooManyRequests

    return isinstance(exc, (ResourceExhausted, TooManyRequests))


def is_oci_throttled(exc: Exception) -> bool:
    from oci.exceptions import ServiceError

    return isinstance(exc, ServiceError) and exc.status == 429


async def with_aws_retry(func: Callable[[], Awaitable[T]], **kwargs) -> T:
    return await with_retry(func, is_aws_throttled, **kwargs)


async def with_azure_retry(func: Callable[[], Awaitable[T]], **kwargs) -> T:
    return await with_retry(func, is_azure_throttled, **kwargs)


async def with_gcp_retry(func: Callable[[], Awaitable[T]], **kwargs) -> T:
    return await with_retry(func, is_gcp_throttled, **kwargs)


async def with_oci_retry(func: Callable[[], Awaitable[T]], **kwargs) -> T:
    return await with_retry(func, is_oci_throttled, **kwargs)

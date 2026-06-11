import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 1
    delay_seconds: float = 0
    backoff_multiplier: float = 1

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds cannot be negative")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")


async def run_with_retries(
    operation: Callable[[], Awaitable[T]],
    retry_config: RetryConfig,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> tuple[T, int]:
    delay = retry_config.delay_seconds
    last_error: Exception | None = None

    for attempt in range(1, retry_config.max_attempts + 1):
        try:
            result = await operation()
            return result, attempt
        except Exception as exc:
            last_error = exc
            if attempt >= retry_config.max_attempts:
                break
            if on_retry:
                on_retry(attempt, exc)
            if delay:
                await asyncio.sleep(delay)
                delay *= retry_config.backoff_multiplier

    if last_error is None:
        raise RuntimeError("Retry execution failed without an exception.")
    raise last_error

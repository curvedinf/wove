"""
Public API functions for Wove, like `merge`.
These functions are designed to be called from within tasks defined
inside a `weave` block.
"""

from typing import Any, Callable, Iterable, Optional
from .vars import merge_context


def merge(
    callable: Callable[..., Any],
    iterable: Optional[Iterable[Any]] = None,
    *,
    retries: Optional[int] = None,
    timeout: Optional[float] = None,
    workers: Optional[int] = None,
    limit_per_minute: Optional[int] = None,
    environment: Optional[str] = None,
    delivery_timeout: Optional[float] = None,
    delivery_idempotency_key: Optional[Any] = None,
    delivery_cancel_mode: Optional[str] = None,
    delivery_heartbeat_seconds: Optional[float] = None,
    delivery_max_in_flight: Optional[int] = None,
    delivery_orphan_policy: Optional[str] = None,
) -> Any:
    """
    Execute a callable from within a running Wove task.

    Parameters
    ----------
    callable
        The async or sync callable to execute.
    iterable
        Optional iterable. When provided, ``callable`` is executed for each
        item (similar to ``@w.do(iterable)`` behavior).
    retries, timeout, workers, limit_per_minute, environment, delivery_*
        The same execution options accepted by ``@w.do``.

    Returns
    -------
    Any
        The callable result, or a list of results when ``iterable`` is provided.

    Raises
    ------
    RuntimeError
        If called outside of an active ``weave`` context.
    """
    merge_implementation = merge_context.get()
    if merge_implementation is None:
        raise RuntimeError(
            "The `merge` function can only be used inside a task "
            "running within an active `weave` block."
        )
    return merge_implementation(
        callable,
        iterable,
        retries=retries,
        timeout=timeout,
        workers=workers,
        limit_per_minute=limit_per_minute,
        environment=environment,
        delivery_timeout=delivery_timeout,
        delivery_idempotency_key=delivery_idempotency_key,
        delivery_cancel_mode=delivery_cancel_mode,
        delivery_heartbeat_seconds=delivery_heartbeat_seconds,
        delivery_max_in_flight=delivery_max_in_flight,
        delivery_orphan_policy=delivery_orphan_policy,
    )

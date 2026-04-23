import asyncio
import inspect
from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    Union,
)

from .helpers import sync_to_async
from .result import WoveResult

_KNOWN_DELIVERY_CANCEL_MODES = {"best_effort", "require_ack"}
_KNOWN_ORPHAN_POLICIES = {"fail", "cancel", "requeue", "detach"}


def do(
    context: Any,
    arg: Optional[Union[Iterable[Any], Callable[..., Any], str]] = None,
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
) -> Callable[..., Any]:
    """Decorator to register a task."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        task_name = func.__name__
        if hasattr(WoveResult, task_name):
            raise NameError(
                f"Task name '{task_name}' conflicts with a built-in "
                "attribute of the WoveResult object and is not allowed."
            )

        map_source = None if callable(arg) else arg
        if (workers is not None or limit_per_minute is not None) and map_source is None:
            raise ValueError(
                "The 'workers' and 'limit_per_minute' parameters can only be used with "
                "mapped tasks (e.g., @w.do(iterable, ...))."
            )

        final_params = {
            "func": func,
            "map_source": map_source,
            "retries": retries,
            "timeout": timeout,
            "workers": workers,
            "limit_per_minute": limit_per_minute,
            "environment": environment,
            "delivery_timeout": delivery_timeout,
            "delivery_idempotency_key": delivery_idempotency_key,
            "delivery_cancel_mode": delivery_cancel_mode,
            "delivery_heartbeat_seconds": delivery_heartbeat_seconds,
            "delivery_max_in_flight": delivery_max_in_flight,
            "delivery_orphan_policy": delivery_orphan_policy,
        }

        if func.__name__ in context._tasks:
            parent_params = context._tasks[func.__name__]
            if final_params["retries"] is None:
                final_params["retries"] = parent_params.get("retries")
            if final_params["timeout"] is None:
                final_params["timeout"] = parent_params.get("timeout")
            if final_params["workers"] is None:
                final_params["workers"] = parent_params.get("workers")
            if final_params["limit_per_minute"] is None:
                final_params["limit_per_minute"] = parent_params.get("limit_per_minute")
            if final_params["environment"] is None:
                final_params["environment"] = parent_params.get("environment")
            if final_params["delivery_timeout"] is None:
                final_params["delivery_timeout"] = parent_params.get("delivery_timeout")
            if final_params["delivery_idempotency_key"] is None:
                final_params["delivery_idempotency_key"] = parent_params.get(
                    "delivery_idempotency_key"
                )
            if final_params["delivery_cancel_mode"] is None:
                final_params["delivery_cancel_mode"] = parent_params.get("delivery_cancel_mode")
            if final_params["delivery_heartbeat_seconds"] is None:
                final_params["delivery_heartbeat_seconds"] = parent_params.get(
                    "delivery_heartbeat_seconds"
                )
            if final_params["delivery_max_in_flight"] is None:
                final_params["delivery_max_in_flight"] = parent_params.get(
                    "delivery_max_in_flight"
                )
            if final_params["delivery_orphan_policy"] is None:
                final_params["delivery_orphan_policy"] = parent_params.get(
                    "delivery_orphan_policy"
                )

        if final_params["retries"] is None:
            final_params["retries"] = context._task_defaults.get("retries")
        if final_params["timeout"] is None:
            final_params["timeout"] = context._task_defaults.get("timeout")
        if final_params["workers"] is None:
            final_params["workers"] = context._task_defaults.get("workers")
        if final_params["limit_per_minute"] is None:
            final_params["limit_per_minute"] = context._task_defaults.get("limit_per_minute")
        if final_params["environment"] is None:
            final_params["environment"] = context._task_defaults.get("environment")
        if final_params["delivery_timeout"] is None:
            final_params["delivery_timeout"] = context._task_defaults.get("delivery_timeout")
        if final_params["delivery_idempotency_key"] is None:
            final_params["delivery_idempotency_key"] = context._task_defaults.get(
                "delivery_idempotency_key"
            )
        if final_params["delivery_cancel_mode"] is None:
            final_params["delivery_cancel_mode"] = context._task_defaults.get(
                "delivery_cancel_mode"
            )
        if final_params["delivery_heartbeat_seconds"] is None:
            final_params["delivery_heartbeat_seconds"] = context._task_defaults.get(
                "delivery_heartbeat_seconds"
            )
        if final_params["delivery_max_in_flight"] is None:
            final_params["delivery_max_in_flight"] = context._task_defaults.get(
                "delivery_max_in_flight"
            )
        if final_params["delivery_orphan_policy"] is None:
            final_params["delivery_orphan_policy"] = context._task_defaults.get(
                "delivery_orphan_policy"
            )

        if final_params["delivery_cancel_mode"] not in _KNOWN_DELIVERY_CANCEL_MODES:
            raise ValueError(
                "delivery_cancel_mode must be one of: 'best_effort', 'require_ack'"
            )
        orphan_policy = final_params["delivery_orphan_policy"]
        if orphan_policy is not None and orphan_policy not in _KNOWN_ORPHAN_POLICIES:
            allowed = "', '".join(sorted(_KNOWN_ORPHAN_POLICIES))
            raise ValueError(f"delivery_orphan_policy must be one of: '{allowed}'")

        context._tasks[func.__name__] = final_params
        if func.__name__ not in context.result._definition_order:
            context.result._definition_order.append(func.__name__)
        return func

    if callable(arg):
        return decorator(arg)
    else:
        return decorator


async def merge(
    context: Any, func: Callable[..., Any], iterable: Optional[Iterable[Any]] = None
) -> Any:
    """Dynamically executes a callable from within a Wove task."""
    if len(context._call_stack) > 100:
        raise RecursionError("Merge call depth exceeded 100")

    func_name = getattr(func, '__name__', 'anonymous_callable')
    context._call_stack.append(func_name)

    try:
        if not inspect.iscoroutinefunction(getattr(func, 'func', func)):
            func = sync_to_async(func)

        if iterable is None:
            res = await func()
            if inspect.iscoroutine(res):
                res = await res
            return res
        else:
            async def run_and_await(item):
                res = await func(item)
                if inspect.iscoroutine(res):
                    res = await res
                return res

            items = list(iterable)
            tasks = [asyncio.create_task(run_and_await(item)) for item in items]
            return await asyncio.gather(*tasks)
    finally:
        context._call_stack.pop()

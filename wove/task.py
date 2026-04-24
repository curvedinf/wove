import asyncio
import inspect
import time
from contextvars import copy_context
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Union,
)

from .helpers import sync_to_async
from .result import WoveResult
from .runtime import runtime

_KNOWN_DELIVERY_CANCEL_MODES = {"best_effort", "require_ack"}
_KNOWN_ORPHAN_POLICIES = {"fail", "cancel", "requeue", "detach"}
_TASK_OPTION_KEYS = (
    "retries",
    "timeout",
    "workers",
    "limit_per_minute",
    "environment",
    "delivery_timeout",
    "delivery_idempotency_key",
    "delivery_cancel_mode",
    "delivery_heartbeat_seconds",
    "delivery_max_in_flight",
    "delivery_orphan_policy",
)


def _resolve_task_options(
    context: Any,
    *,
    map_source: Optional[Any],
    inherited: Optional[Dict[str, Any]] = None,
    **options: Any,
) -> Dict[str, Any]:
    final_params = dict(options)

    if inherited is not None:
        for key in _TASK_OPTION_KEYS:
            if final_params[key] is None:
                final_params[key] = inherited.get(key)

    for key in _TASK_OPTION_KEYS:
        if final_params[key] is None:
            final_params[key] = context._task_defaults.get(key)

    if (
        final_params["workers"] is not None
        or final_params["limit_per_minute"] is not None
    ) and map_source is None:
        raise ValueError(
            "The 'workers' and 'limit_per_minute' parameters can only be used with "
            "mapped tasks (e.g., @w.do(iterable, ...) or merge(func, iterable, ...))."
        )

    if final_params["delivery_cancel_mode"] not in _KNOWN_DELIVERY_CANCEL_MODES:
        raise ValueError(
            "delivery_cancel_mode must be one of: 'best_effort', 'require_ack'"
        )
    orphan_policy = final_params["delivery_orphan_policy"]
    if orphan_policy is not None and orphan_policy not in _KNOWN_ORPHAN_POLICIES:
        allowed = "', '".join(sorted(_KNOWN_ORPHAN_POLICIES))
        raise ValueError(f"delivery_orphan_policy must be one of: '{allowed}'")

    return final_params


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

        final_params = _resolve_task_options(
            context,
            map_source=map_source,
            inherited=context._tasks.get(func.__name__),
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
        final_params["func"] = func
        final_params["map_source"] = map_source

        context._tasks[func.__name__] = final_params
        if func.__name__ not in context.result._definition_order:
            context.result._definition_order.append(func.__name__)
        return func

    if callable(arg):
        return decorator(arg)
    else:
        return decorator


def merge(
    context: Any,
    func: Callable[..., Any],
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
    """Dynamically executes a callable from within a Wove task."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        sync_caller = True
    else:
        sync_caller = False

    coroutine = _merge_async(
        context,
        func,
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
        _sync_caller=sync_caller,
    )

    if sync_caller:
        loop = getattr(context, "_loop", None)
        if loop is None or loop.is_closed():
            coroutine.close()
            raise RuntimeError(
                "The `merge` function can only be used inside a task "
                "running within an active `weave` block."
            )
        return asyncio.run_coroutine_threadsafe(coroutine, loop).result()

    return coroutine


async def _merge_async(
    context: Any,
    func: Callable[..., Any],
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
    _sync_caller: bool = False,
) -> Any:
    if context._executor_runtime is None:
        raise RuntimeError(
            "The `merge` function can only be used inside a task "
            "running within an active `weave` block."
        )
    if len(context._call_stack) > 100:
        raise RecursionError("Merge call depth exceeded 100")

    func_name = getattr(func, '__name__', 'anonymous_callable')
    task_name = f"merge:{func_name}"
    task_info = _resolve_task_options(
        context,
        map_source=iterable,
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
    environment_name = task_info["environment"]
    environment_definition = runtime.resolve_environment_settings(environment_name)
    await context._executor_runtime.ensure_environment(
        environment_name,
        environment_definition,
    )

    context._call_stack.append(func_name)
    try:
        if iterable is None:
            return await _run_merge_callable(
                context,
                task_name=task_name,
                task_func=func,
                task_args={},
                task_info=task_info,
                sync_caller=_sync_caller,
            )

        items = list(iterable)
        if context._max_pending is not None and len(items) > context._max_pending:
            raise RuntimeError(
                f"Merged callable '{func_name}' has {len(items)} items, "
                f"which exceeds max_pending={context._max_pending}."
            )

        workers = task_info.get("workers")
        semaphore = asyncio.Semaphore(workers) if workers else None
        limit_per_minute = task_info.get("limit_per_minute")
        delay = 60.0 / limit_per_minute if limit_per_minute else 0

        async def run_item(item: Any, index: int) -> Any:
            if limit_per_minute and index > 0:
                await asyncio.sleep(index * delay)

            async def run() -> Any:
                return await _run_merge_callable(
                    context,
                    task_name=task_name,
                    task_func=_merge_item_callable(func),
                    task_args={"item": item},
                    task_info=task_info,
                    sync_caller=_sync_caller,
                )

            if semaphore is None:
                return await run()
            async with semaphore:
                return await run()

        tasks = [
            asyncio.create_task(run_item(item, index))
            for index, item in enumerate(items)
        ]
        return await asyncio.gather(*tasks)
    finally:
        context._call_stack.pop()


def _merge_item_callable(func: Callable[..., Any]) -> Callable[..., Any]:
    if not inspect.iscoroutinefunction(getattr(func, "func", func)):
        def call_sync_item(item: Any) -> Any:
            return func(item)

        return call_sync_item

    async def call_item(item: Any) -> Any:
        result = func(item)
        if inspect.iscoroutine(result):
            return await result
        return result

    return call_item


def _sync_to_async_default_executor(func: Callable[..., Any]) -> Callable[..., Any]:
    async def run_in_default_executor(*args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        context = copy_context()
        return await loop.run_in_executor(
            None,
            lambda: context.run(lambda: func(*args, **kwargs)),
        )

    return run_in_default_executor


async def _run_merge_callable(
    context: Any,
    *,
    task_name: str,
    task_func: Callable[..., Any],
    task_args: Dict[str, Any],
    task_info: Dict[str, Any],
    sync_caller: bool,
) -> Any:
    environment_name = task_info.get("environment")
    run_func = task_func
    if (
        context._executor_runtime.is_local_environment(environment_name)
        and not inspect.iscoroutinefunction(getattr(run_func, "func", run_func))
    ):
        # A sync task calling merge is already occupying one Wove worker thread.
        # Re-entering the same executor can deadlock when max_workers is small.
        if sync_caller:
            run_func = _sync_to_async_default_executor(run_func)
        else:
            run_func = sync_to_async(run_func)

    retries = task_info.get("retries", 0) or 0
    timeout = task_info.get("timeout")
    last_exception = None
    for _attempt in range(retries + 1):
        started_at = time.monotonic()
        try:
            coroutine = context._executor_runtime.run_task(
                task_name=task_name,
                task_func=run_func,
                task_args=task_args,
                task_info=task_info,
            )
            if timeout is None:
                result = await coroutine
            else:
                result = await asyncio.wait_for(coroutine, timeout=timeout)
            if inspect.iscoroutine(result):
                return await result
            return result
        except asyncio.TimeoutError:
            raise asyncio.CancelledError from None
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            last_exception = exc
        finally:
            context.result._add_timing(task_name, time.monotonic() - started_at)
    raise last_exception from None

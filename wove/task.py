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


def do(
    context: Any,
    arg: Optional[Union[Iterable[Any], Callable[..., Any], str]] = None,
    *,
    retries: int = 0,
    timeout: Optional[float] = None,
    workers: Optional[int] = None,
    limit_per_minute: Optional[int] = None,
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
        }

        if func.__name__ in context._tasks:
            parent_params = context._tasks[func.__name__]
            if final_params["retries"] == 0:
                final_params["retries"] = parent_params.get("retries", 0)
            if final_params["timeout"] is None:
                final_params["timeout"] = parent_params.get("timeout")
            if final_params["workers"] is None:
                final_params["workers"] = parent_params.get("workers")
            if final_params["limit_per_minute"] is None:
                final_params["limit_per_minute"] = parent_params.get("limit_per_minute")

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

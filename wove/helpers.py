import asyncio
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

R = TypeVar("R")


def sync_to_async(func: Callable[..., R]) -> Callable[..., Coroutine[Any, Any, R]]:
    """
    Wraps a synchronous function to run in asyncio's default thread pool.

    This allows a blocking synchronous function to be called from an async
    context without blocking the event loop. It's a simplified version of
    what libraries like `asgiref` provide.

    Args:
        func: The synchronous function to wrap.

    Returns:
        An awaitable coroutine function that executes the original function
        in a separate thread.
    """

    @wraps(func)
    async def run_in_executor(*args: Any, **kwargs: Any) -> R:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    return run_in_executor

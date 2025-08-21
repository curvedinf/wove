import asyncio
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

from .vars import executor_context

R = TypeVar("R")


def sync_to_async(func: Callable[..., R]) -> Callable[..., Coroutine[Any, Any, R]]:
    """
    Wraps a synchronous function to run in an executor.

    By default, it uses asyncio's default thread pool, but if called from
    within a `weave` context, it will use the dedicated executor for that
    context. This prevents deadlocks when a `weave` block is used inside
    another system that also manages the default executor (like Quart).

    Args:
        func: The synchronous function to wrap.

    Returns:
        An awaitable coroutine function that executes the original function
        in a separate thread.
    """

    @wraps(func)
    async def run_in_executor(*args: Any, **kwargs: Any) -> R:
        loop = asyncio.get_running_loop()
        # Get the executor from the context. If not in a weave context,
        # it will be None, and asyncio will use its default executor.
        executor = executor_context.get()
        return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))

    return run_in_executor


def flatten(list_of_lists):
    """Converts a 2D iterable into a 1D list."""
    return [item for sublist in list_of_lists for item in sublist]


def fold(a_list, size):
    """Converts a 1D list into a list of smaller lists of a given size."""
    if size <= 0:
        raise ValueError("Fold size must be a positive integer.")
    return [a_list[i : i + size] for i in range(0, len(a_list), size)]


def undict(a_dict):
    """Converts a dictionary into a list of [key, value] pairs."""
    return list(a_dict.items())


def redict(list_of_pairs):
    """Converts a list of key-value pairs back into a dictionary."""
    return dict(list_of_pairs)


def denone(an_iterable):
    """Removes all None values from an iterable."""
    return [item for item in an_iterable if item is not None]

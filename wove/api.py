"""
Public API functions for Wove, like `merge`.
These functions are designed to be called from within tasks defined
inside a `weave` block.
"""

from typing import Any, Callable, Iterable, Optional
from .vars import merge_context


def merge(
    callable: Callable[..., Any], iterable: Optional[Iterable[Any]] = None
) -> Any:
    """
    Dynamically executes a callable from within a Wove task, integrating
    its result into the dependency graph.
    This function can only be called from within a task running inside an
    active `weave` context.
    Args:
        callable: The async or sync function to execute.
        iterable: An optional iterable. If provided, the callable will be
            executed concurrently for each item, similar to `@w.do(iterable)`.
    Returns:
        The result of the callable, or a list of results if an iterable
        was provided.
    Raises:
        RuntimeError: If called outside of an active `weave` context.
    """
    merge_implementation = merge_context.get()
    if merge_implementation is None:
        raise RuntimeError(
            "The `merge` function can only be used inside a task "
            "running within an active `async with weave()` block."
        )
    return merge_implementation(callable, iterable)

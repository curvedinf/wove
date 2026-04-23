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
    Execute a callable from within a running Wove task.

    Parameters
    ----------
    callable
        The async or sync callable to execute.
    iterable
        Optional iterable. When provided, ``callable`` is executed for each
        item (similar to ``@w.do(iterable)`` behavior).

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
            "running within an active `async with weave()` block."
        )
    return merge_implementation(callable, iterable)

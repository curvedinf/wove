from typing import Any, Callable, TypeVar

from .vars import current_weave_context

F = TypeVar("F", bound=Callable[..., Any])


def do(func: F) -> F:
    """
    A decorator to register a function as a concurrent task within a `weave` context.

    When a function is decorated with `@do` inside an `async with weave()` block,
    it is added to a dependency graph. Wove will then execute it concurrently
    with other tasks, respecting any dependencies inferred from its signature.

    Raises:
        RuntimeError: If used outside of an `async with weave()` block.

    Returns:
        The original function, unchanged.
    """
    ctx = current_weave_context.get()
    if ctx is None:
        raise RuntimeError(
            "The @do decorator can only be used inside an 'async with weave()' block."
        )

    ctx._register_task(func)
    return func

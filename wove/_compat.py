import asyncio
import contextvars
import functools
from typing import Any, Callable


async def to_thread(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Run a blocking callable in the default executor.

    Python 3.9 added asyncio.to_thread. Wove supports Python 3.8, so runtime code
    uses this compatibility wrapper anywhere the standard helper would be used.
    """

    native_to_thread = getattr(asyncio, "to_thread", None)
    if native_to_thread is not None:
        return await native_to_thread(func, *args, **kwargs)

    loop = asyncio.get_running_loop()
    context = contextvars.copy_context()
    call = functools.partial(context.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, call)

from typing import Optional, Callable, Union, Iterable


from .vars import executor_context


class Weave:
    """
    A base class for creating inheritable, reusable workflows.

    Tasks are defined as methods using the `@Weave.do` decorator. These
    workflows can then be passed to the `weave` context manager and
    customized inline.
    """
    def __init__(self):
        if executor_context.get() is None:
            raise TypeError(
                f"'{type(self).__name__}' cannot be instantiated directly. "
                "Instead, pass the class to the `weave()` context manager, "
                "e.g., `async with weave(MyWorkflow):`"
            )

    @staticmethod
    def do(
        arg: Optional[Union[Callable, str, Iterable]] = None,
        *,
        retries: int = 0,
        timeout: Optional[float] = None,
        workers: Optional[int] = None,
        limit_per_minute: Optional[int] = None,
    ) -> Callable:
        """
        A decorator for defining a task within a Weave class.

        This is the class-based equivalent of the `@w.do` decorator used
        inside a `weave` block. It accepts the same parameters.
        """

        def decorator(func: Callable) -> Callable:
            # Attach the parameters to the function object itself.
            # The WoveContextManager will inspect the Weave class
            # for these attributes to build the initial task set.
            map_source = None if callable(arg) else arg
            func._wove_task_info = {
                "map_source": map_source,
                "retries": retries,
                "timeout": timeout,
                "workers": workers,
                "limit_per_minute": limit_per_minute,
            }
            return func

        if callable(arg):
            # Called as @Weave.do or @w.do(callable_func)
            return decorator(arg)
        else:
            # Called as @Weave.do(...) with parameters
            return decorator

from typing import Optional, Callable


class Weave:
    """
    A base class for creating inheritable, reusable workflows.

    Tasks are defined as methods using the `@Weave.do` decorator. These
    workflows can then be passed to the `weave` context manager and
    customized inline.
    """

    @staticmethod
    def do(
        _func: Optional[Callable] = None,
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
            func._wove_task_info = {
                "retries": retries,
                "timeout": timeout,
                "workers": workers,
                "limit_per_minute": limit_per_minute,
            }
            return func

        if _func is None:
            # Called as @Weave.do(...) with parameters
            return decorator
        else:
            # Called as @Weave.do without parameters
            return decorator(_func)

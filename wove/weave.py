from typing import Optional, Callable, Union, Iterable


from .vars import executor_context

_KNOWN_DELIVERY_CANCEL_MODES = {"best_effort", "require_ack"}
_KNOWN_ORPHAN_POLICIES = {"fail", "cancel", "requeue", "detach"}


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
        retries: Optional[int] = None,
        timeout: Optional[float] = None,
        workers: Optional[int] = None,
        limit_per_minute: Optional[int] = None,
        environment: Optional[str] = None,
        delivery_timeout: Optional[float] = None,
        delivery_idempotency_key: Optional[object] = None,
        delivery_cancel_mode: Optional[str] = None,
        delivery_heartbeat_seconds: Optional[float] = None,
        delivery_max_in_flight: Optional[int] = None,
        delivery_orphan_policy: Optional[str] = None,
    ) -> Callable:
        """
        A decorator for defining a task within a Weave class.

        This is the class-based equivalent of the `@w.do` decorator used
        inside a `weave` block. It accepts the same parameters.
        """

        def decorator(func: Callable) -> Callable:
            if delivery_cancel_mode is not None and delivery_cancel_mode not in _KNOWN_DELIVERY_CANCEL_MODES:
                raise ValueError("delivery_cancel_mode must be one of: 'best_effort', 'require_ack'")
            if delivery_orphan_policy is not None and delivery_orphan_policy not in _KNOWN_ORPHAN_POLICIES:
                allowed = "', '".join(sorted(_KNOWN_ORPHAN_POLICIES))
                raise ValueError(f"delivery_orphan_policy must be one of: '{allowed}'")
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
                "environment": environment,
                "delivery_timeout": delivery_timeout,
                "delivery_idempotency_key": delivery_idempotency_key,
                "delivery_cancel_mode": delivery_cancel_mode,
                "delivery_heartbeat_seconds": delivery_heartbeat_seconds,
                "delivery_max_in_flight": delivery_max_in_flight,
                "delivery_orphan_policy": delivery_orphan_policy,
            }
            return func

        if callable(arg):
            # Called as @Weave.do or @w.do(callable_func)
            return decorator(arg)
        else:
            # Called as @Weave.do(...) with parameters
            return decorator

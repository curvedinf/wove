import asyncio
import functools
import inspect
import subprocess
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Type

from .debug import print_debug_report
from .environment import ExecutorRuntime
from .executor import execute_plan
from .graph import build_graph_and_plan
from .result import WoveResult
from .runtime import runtime
from .serialization import dispatch_dump
from .task import do as do_decorator, merge as merge_func
from .weave import Weave
from .vars import executor_context, merge_context


def _coalesce(value: Any, default: Any) -> Any:
    return default if value is None else value


class WoveContextManager:
    """
    The core context manager that discovers, orchestrates, and executes tasks
    defined within a `with weave()` or `async with weave()` block.
    """

    def __init__(
        self,
        parent_weave: Optional[Type["Weave"]] = None,
        *,
        debug: bool = False,
        environment: Optional[str] = None,
        max_workers: Optional[int] = None,
        background: Optional[bool] = None,
        fork: Optional[bool] = None,
        on_done: Optional[Callable] = None,
        max_pending: Optional[int] = None,
        error_mode: Optional[str] = None,
        delivery_timeout: Optional[float] = None,
        delivery_idempotency_key: Optional[Any] = None,
        delivery_cancel_mode: Optional[str] = None,
        delivery_heartbeat_seconds: Optional[float] = None,
        delivery_max_in_flight: Optional[int] = None,
        delivery_orphan_policy: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        resolved_environment = runtime.resolve_environment_name(environment)
        resolved_settings = runtime.resolve_environment_settings(resolved_environment)

        self._debug = debug
        self._environment = resolved_environment
        self._max_workers = _coalesce(max_workers, resolved_settings.get("max_workers"))
        self._background = _coalesce(background, resolved_settings.get("background"))
        self._fork = _coalesce(fork, resolved_settings.get("fork"))
        self._max_pending = _coalesce(max_pending, resolved_settings.get("max_pending"))
        self._error_mode = _coalesce(error_mode, resolved_settings.get("error_mode"))
        if self._error_mode not in {"raise", "return"}:
            raise ValueError("error_mode must be one of: 'raise', 'return'")

        self._task_defaults = {
            "retries": resolved_settings.get("retries"),
            "timeout": resolved_settings.get("timeout"),
            "workers": resolved_settings.get("workers"),
            "limit_per_minute": resolved_settings.get("limit_per_minute"),
            "environment": resolved_environment,
            "delivery_timeout": _coalesce(
                delivery_timeout, resolved_settings.get("delivery_timeout")
            ),
            "delivery_idempotency_key": _coalesce(
                delivery_idempotency_key, resolved_settings.get("delivery_idempotency_key")
            ),
            "delivery_cancel_mode": _coalesce(
                delivery_cancel_mode, resolved_settings.get("delivery_cancel_mode")
            ),
            "delivery_heartbeat_seconds": _coalesce(
                delivery_heartbeat_seconds, resolved_settings.get("delivery_heartbeat_seconds")
            ),
            "delivery_max_in_flight": _coalesce(
                delivery_max_in_flight, resolved_settings.get("delivery_max_in_flight")
            ),
            "delivery_orphan_policy": _coalesce(
                delivery_orphan_policy, resolved_settings.get("delivery_orphan_policy")
            ),
        }

        self._on_done_callback = on_done
        self._executor: Optional[ThreadPoolExecutor] = None
        self._executor_runtime: Optional[ExecutorRuntime] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._tasks: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.result = WoveResult(error_mode=self._error_mode)
        self.execution_plan: Optional[Dict[str, Any]] = None
        self._call_stack: List[str] = []
        self._merge_token = None
        self._executor_token = None
        self.do = functools.partial(do_decorator, self)
        self._merge = functools.partial(merge_func, self)

        self._tasks["data"] = {
            "func": lambda: kwargs,
            "map_source": None,
            "seed": True,
            "environment": self._environment,
            "retries": 0,
            "timeout": None,
            "workers": None,
            "limit_per_minute": None,
            "delivery_timeout": None,
            "delivery_idempotency_key": None,
            "delivery_cancel_mode": self._task_defaults["delivery_cancel_mode"],
            "delivery_heartbeat_seconds": None,
            "delivery_max_in_flight": None,
            "delivery_orphan_policy": None,
        }
        self.result._add_result("data", kwargs)

        for name, value in kwargs.items():
            if hasattr(WoveResult, name):
                raise NameError(
                    f"Initial value name '{name}' conflicts with a built-in attribute."
                )
            if name == "data":
                raise NameError("'data' is a reserved name.")
            self.result._add_result(name, value)
            self._tasks[name] = {
                "func": (lambda v=value: v),
                "map_source": None,
                "seed": True,
                "environment": self._environment,
                "retries": 0,
                "timeout": None,
                "workers": None,
                "limit_per_minute": None,
                "delivery_timeout": None,
                "delivery_idempotency_key": None,
                "delivery_cancel_mode": self._task_defaults["delivery_cancel_mode"],
                "delivery_heartbeat_seconds": None,
                "delivery_max_in_flight": None,
                "delivery_orphan_policy": None,
            }

        self.parent_weave = parent_weave if parent_weave else None

    def _load_from_parent(self, parent_weave_instance: "Weave") -> None:
        """
        Inspect a Weave class and pre-populate inherited tasks.
        """
        for name, member in inspect.getmembers(type(parent_weave_instance), inspect.isfunction):
            if not hasattr(member, "_wove_task_info"):
                continue
            task_info = member._wove_task_info
            bound_method = functools.partial(member, parent_weave_instance)
            self._tasks[name] = {
                "func": bound_method,
                "map_source": task_info.get("map_source"),
                "retries": _coalesce(task_info.get("retries"), self._task_defaults["retries"]),
                "timeout": _coalesce(task_info.get("timeout"), self._task_defaults["timeout"]),
                "workers": _coalesce(task_info.get("workers"), self._task_defaults["workers"]),
                "limit_per_minute": _coalesce(
                    task_info.get("limit_per_minute"), self._task_defaults["limit_per_minute"]
                ),
                "environment": _coalesce(task_info.get("environment"), self._task_defaults["environment"]),
                "delivery_timeout": _coalesce(
                    task_info.get("delivery_timeout"), self._task_defaults["delivery_timeout"]
                ),
                "delivery_idempotency_key": _coalesce(
                    task_info.get("delivery_idempotency_key"),
                    self._task_defaults["delivery_idempotency_key"],
                ),
                "delivery_cancel_mode": _coalesce(
                    task_info.get("delivery_cancel_mode"),
                    self._task_defaults["delivery_cancel_mode"],
                ),
                "delivery_heartbeat_seconds": _coalesce(
                    task_info.get("delivery_heartbeat_seconds"),
                    self._task_defaults["delivery_heartbeat_seconds"],
                ),
                "delivery_max_in_flight": _coalesce(
                    task_info.get("delivery_max_in_flight"),
                    self._task_defaults["delivery_max_in_flight"],
                ),
                "delivery_orphan_policy": _coalesce(
                    task_info.get("delivery_orphan_policy"),
                    self._task_defaults["delivery_orphan_policy"],
                ),
            }
            if name not in self.result._definition_order:
                self.result._definition_order.append(name)

    def __enter__(self) -> "WoveContextManager":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        if exc_type:
            return

        async def _runner() -> None:
            await self.__aenter__()
            await self.__aexit__(None, None, None)

        asyncio.run(_runner())

    async def __aenter__(self) -> "WoveContextManager":
        self._loop = asyncio.get_running_loop()
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        self._executor_token = executor_context.set(self._executor)
        self._merge_token = merge_context.set(self._merge)
        if self.parent_weave:
            instance_to_load = (
                self.parent_weave() if inspect.isclass(self.parent_weave) else self.parent_weave
            )
            self._load_from_parent(instance_to_load)
        return self

    def _start_threaded_process(self) -> None:
        """
        Execute the weave in a new background thread.
        """

        def thread_target() -> None:
            asyncio.run(self._run_background_weave())

        thread = threading.Thread(target=thread_target)
        thread.start()

    def _start_forked_process(self) -> None:
        """
        Execute the weave in a detached process.
        """
        # The executor and context tokens are not pickleable and should be
        # recreated in the new process.
        self._executor = None
        self._executor_token = None
        self._merge_token = None
        self._executor_runtime = None
        self._loop = None

        with tempfile.NamedTemporaryFile(delete=False) as f:
            dispatch_dump(
                self,
                f,
                reason="forked background execution serializes the weave context into a detached process.",
            )
            context_file = f.name

        command = [sys.executable, "-m", "wove.background", context_file]
        subprocess.Popen(command)

    async def _run_background_weave(self) -> None:
        """
        Helper to run the weave and invoke on_done callback.
        """
        self._background = False
        try:
            async with self:
                pass
        finally:
            self._background = True

        if self._on_done_callback:
            if asyncio.iscoroutinefunction(self._on_done_callback):
                await self._on_done_callback(self.result)
            else:
                self._on_done_callback(self.result)

    def _collect_environment_definitions(self) -> Dict[str, Dict[str, Any]]:
        names = {self._environment}
        for task_name, task_info in self._tasks.items():
            if task_info.get("seed"):
                continue
            environment_name = task_info.get("environment") or self._environment
            names.add(environment_name)

        definitions: Dict[str, Dict[str, Any]] = {}
        for name in names:
            definitions[name] = runtime.resolve_environment_settings(name)
        return definitions

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        if self._background:
            if self._fork:
                self._start_forked_process()
            else:
                self._start_threaded_process()
            return

        if exc_type:
            if self._executor:
                self._executor.shutdown(wait=False)
            return

        try:
            planning_start_time = time.monotonic()
            self.execution_plan = build_graph_and_plan(
                self._tasks,
                self.result._results,
                self.result._definition_order,
            )
            planning_end_time = time.monotonic()
            self.result._add_timing("planning", planning_end_time - planning_start_time)
        except (NameError, TypeError, RuntimeError) as error:
            for task_name in self._tasks:
                if task_name not in self.result._results:
                    self.result._add_error(task_name, error)
            raise

        if self._debug:
            print_debug_report(self.execution_plan, self._tasks, self.result._results)

        run_config = {
            "error_mode": self._error_mode,
            "max_pending": self._max_pending,
            "delivery_heartbeat_seconds": self._task_defaults["delivery_heartbeat_seconds"],
            "delivery_orphan_policy": self._task_defaults["delivery_orphan_policy"],
        }
        self._executor_runtime = ExecutorRuntime(self._collect_environment_definitions(), run_config)
        await self._executor_runtime.start()

        try:
            await execute_plan(self.execution_plan, self._tasks, self.result, self)
        finally:
            if self._executor_runtime:
                await self._executor_runtime.stop()
                self._executor_runtime = None
            if self._executor:
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        await loop.run_in_executor(None, self._executor.shutdown)
                except RuntimeError:
                    pass
            if self._executor_token:
                executor_context.reset(self._executor_token)
            if self._merge_token:
                merge_context.reset(self._merge_token)
            self._loop = None

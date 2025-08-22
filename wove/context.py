import asyncio
import inspect
import functools
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
)

from .debug import print_debug_report
from .executor import execute_plan
from .graph import build_graph_and_plan
from .helpers import sync_to_async
from .result import WoveResult
from .task import do as do_decorator, merge as merge_func
from .weave import Weave
from .vars import merge_context, executor_context


class WoveContextManager:
    """
    The core context manager that discovers, orchestrates, and executes tasks
    defined within an `async with weave()` block.
    """

    def __init__(
        self,
        parent_weave: Optional[Type["Weave"]] = None,
        *,
        debug: bool = False,
        max_workers: Optional[int] = 256,
        **kwargs,
    ) -> None:
        """
        Initializes the context manager.
        """
        self._debug = debug
        self._max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        self._tasks: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.result = WoveResult()
        self.execution_plan: Optional[Dict[str, Any]] = None
        self._call_stack: List[str] = []
        self._merge_token = None
        self._executor_token = None
        self.do = functools.partial(do_decorator, self)
        self._merge = functools.partial(merge_func, self)

        self._tasks["data"] = {"func": lambda: kwargs, "map_source": None, "seed": True}
        self.result._add_result("data", kwargs)

        for name, value in kwargs.items():
            if hasattr(WoveResult, name):
                raise NameError(
                    f"Initial value name '{name}' conflicts with a built-in attribute."
                )
            if name == "data":
                raise NameError("'data' is a reserved name.")
            self.result._add_result(name, value)
            self._tasks[name] = {"func": (lambda v=value: v), "map_source": None, "seed": True}

        if parent_weave:
            instance_to_load = parent_weave() if inspect.isclass(parent_weave) else parent_weave
            self._load_from_parent(instance_to_load)

    def _load_from_parent(self, parent_weave_instance: "Weave") -> None:
        """Inspects a Weave class and pre-populates tasks."""
        for name, member in inspect.getmembers(type(parent_weave_instance), inspect.isfunction):
            if hasattr(member, "_wove_task_info"):
                task_info = member._wove_task_info
                bound_method = functools.partial(member, parent_weave_instance)
                self._tasks[name] = {
                    "func": bound_method,
                    "map_source": task_info.get("map_source"),
                    "retries": task_info.get("retries", 0),
                    "timeout": task_info.get("timeout"),
                    "workers": task_info.get("workers"),
                    "limit_per_minute": task_info.get("limit_per_minute"),
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

        async def _runner():
            await self.__aenter__()
            await self.__aexit__(None, None, None)

        asyncio.run(_runner())

    async def __aenter__(self) -> "WoveContextManager":
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        self._executor_token = executor_context.set(self._executor)
        self._merge_token = merge_context.set(self._merge)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        if exc_type:
            if self._executor:
                self._executor.shutdown(wait=False)
            return

        try:
            planning_start_time = time.monotonic()
            self.execution_plan = build_graph_and_plan(self._tasks, self.result._results, self.result._definition_order)
            planning_end_time = time.monotonic()
            self.result._add_timing("planning", planning_end_time - planning_start_time)
        except (NameError, TypeError, RuntimeError) as e:
            for task_name in self._tasks:
                if task_name not in self.result._results:
                    self.result._add_error(task_name, e)
            raise

        if self._debug:
            print_debug_report(self.execution_plan, self._tasks, self.result._results)

        try:
            await execute_plan(self.execution_plan, self._tasks, self.result, self)
        finally:
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

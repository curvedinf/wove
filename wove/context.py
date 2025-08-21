import asyncio
import inspect
import functools
import time
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Set,
    Type,
    Union,
    Iterable,
)
from .helpers import sync_to_async
from .result import WoveResult
from .weave import Weave
from .vars import merge_context, executor_context


class WoveContextManager:
    """
    The core context manager that discovers, orchestrates, and executes tasks
    defined within an `async with weave()` block.

    It builds a dependency graph of tasks, sorts them topologically, and executes
    them with maximum concurrency while respecting dependencies. It handles both
    `async` and synchronous functions, running the latter in a thread pool.
    """

    def __init__(
        self,
        parent_weave: Optional[Type["Weave"]] = None,
        *,
        debug: bool = False,
        max_workers: Optional[int] = None,
        **initial_values,
    ) -> None:
        """
        Initializes the context manager.

        Args:
            parent_weave: An optional Weave class to inherit tasks from.
            debug: If True, prints a detailed execution plan.
            max_workers: The maximum number of threads for running sync tasks.
                If None, a default value is chosen by ThreadPoolExecutor.
            **initial_values: Keyword arguments to be used as initial seed
                values for the dependency graph.
        """
        self._debug = debug
        self._max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        self._tasks: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.result = WoveResult()
        self.execution_plan: Optional[Dict[str, Any]] = None
        self._call_stack: List[str] = []

        # Seed the graph with initial values.
        for name, value in initial_values.items():
            if hasattr(WoveResult, name):
                raise NameError(
                    f"Initial value name '{name}' conflicts with a built-in "
                    "attribute of the WoveResult object and is not allowed."
                )
            self.result._add_result(name, value)
            self._tasks[name] = {"func": lambda: value, "map_source": None}

        if parent_weave:
            self._load_from_parent(parent_weave)

    def _load_from_parent(self, parent_weave: Type["Weave"]) -> None:
        """Inspects a Weave class and pre-populates the tasks."""
        for name, member in inspect.getmembers(parent_weave, inspect.isfunction):
            if hasattr(member, "_wove_task_info"):
                task_info = member._wove_task_info
                bound_method = functools.partial(member, parent_weave())

                self._tasks[name] = {
                    "func": bound_method,
                    "map_source": None,
                    "retries": task_info.get("retries", 0),
                    "timeout": task_info.get("timeout"),
                    "workers": task_info.get("workers"),
                    "limit_per_minute": task_info.get("limit_per_minute"),
                }
                if name not in self.result._definition_order:
                    self.result._definition_order.append(name)

    def __enter__(self) -> "WoveContextManager":
        """Enters the synchronous context."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """
        Exits the synchronous context and runs the entire async workflow.
        """
        if exc_type:
            return

        async def _runner() -> None:
            await self.__aenter__()
            await self.__aexit__(None, None, None)

        asyncio.run(_runner())

    async def __aenter__(self) -> "WoveContextManager":
        """
        Enters the asynchronous context, creates a dedicated thread pool,
        and prepares for task registration.
        """
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        self._executor_token = executor_context.set(self._executor)
        return self

    def _build_graph_and_plan(self) -> None:
        """
        Builds the dependency graph, sorts it topologically, and creates an
        execution plan in tiers. Populates `self.execution_plan`.
        """
        all_task_names = set(self._tasks.keys())
        dependencies: Dict[str, Set[str]] = {}
        for name, task_info in self._tasks.items():
            # Seed values are not real tasks, they have no dependencies.
            is_seed = name in self.result._results and not hasattr(task_info["func"], '_wove_task_info') and not name in self.result._definition_order
            if is_seed:
                 dependencies[name] = set()
                 continue
            params = set(inspect.signature(task_info["func"]).parameters.keys())
            task_dependencies = params & all_task_names
            if task_info.get("map_source") is not None:
                if isinstance(task_info["map_source"], str):
                    map_source_name = task_info["map_source"]
                    if map_source_name not in all_task_names:
                        raise NameError(
                            f"Mapped task '{name}' depends on '{map_source_name}', but no task with that name was found."
                        )
                    task_dependencies.add(map_source_name)
                non_dependency_params = params - all_task_names
                if len(non_dependency_params) != 1:
                    raise TypeError(
                        f"Mapped task '{name}' must have exactly one parameter that is not a dependency."
                    )
                task_info["item_param"] = non_dependency_params.pop()
            dependencies[name] = task_dependencies

        dependents: Dict[str, Set[str]] = {name: set() for name in self._tasks}
        for name, params in dependencies.items():
            for param in params:
                if param in dependents:
                    dependents[param].add(name)

        in_degree: Dict[str, int] = {
            name: len(params) for name, params in dependencies.items()
        }
        queue: deque[str] = deque(
            [name for name, degree in in_degree.items() if degree == 0]
        )
        sorted_tasks: List[str] = []
        temp_in_degree = in_degree.copy()
        sort_queue = queue.copy()
        while sort_queue:
            task_name = sort_queue.popleft()
            sorted_tasks.append(task_name)
            for dependent in dependents.get(task_name, set()):
                temp_in_degree[dependent] -= 1
                if temp_in_degree[dependent] == 0:
                    sort_queue.append(dependent)
        if len(sorted_tasks) != len(self._tasks):
            raise RuntimeError("Circular dependency detected.")

        tiers: List[List[str]] = []
        tier_build_queue = queue.copy()
        while tier_build_queue:
            current_tier = list(tier_build_queue)
            tiers.append(current_tier)
            next_tier_queue = deque()
            for task_name in current_tier:
                for dependent in dependents.get(task_name, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_tier_queue.append(dependent)
            tier_build_queue = next_tier_queue

        self.execution_plan = {
            "dependencies": dependencies,
            "dependents": dependents,
            "tiers": tiers,
            "sorted_tasks": sorted_tasks,
        }

    def _print_debug_report(self) -> None:
        # ... (implementation unchanged for brevity)
        pass

    async def _retry_timeout_wrapper(
        self, task_name: str, task_func: Callable, args: Dict
    ) -> Any:
        task_info = self._tasks[task_name]
        retries = task_info.get("retries", 0)
        timeout = task_info.get("timeout")
        last_exception = None
        for attempt in range(retries + 1):
            coro = task_func(**args)
            try:
                if timeout is not None:
                    return await asyncio.wait_for(coro, timeout=timeout)
                else:
                    return await coro
            except (Exception, asyncio.TimeoutError) as e:
                last_exception = e
        raise last_exception from None

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        if exc_type:
            return

        try:
            self._build_graph_and_plan()
        except (NameError, TypeError, RuntimeError) as e:
            # For graph-building errors, we fail fast.
            raise e

        if self._debug:
            self._print_debug_report()

        tiers = self.execution_plan["tiers"]
        dependencies = self.execution_plan["dependencies"]
        all_created_tasks: Set[asyncio.Future] = set()

        try:
            for tier in tiers:
                tier_futures: Dict[asyncio.Future, str] = {}
                for task_name in tier:
                    task_info = self._tasks[task_name]
                    task_func = task_info["func"]
                    args = {p: self.result._results[p] for p in dependencies[task_name]}

                    if not inspect.iscoroutinefunction(task_func):
                        task_func = sync_to_async(task_func)

                    coro = self._retry_timeout_wrapper(task_name, task_func, args)
                    future = asyncio.create_task(coro)
                    tier_futures[future] = task_name
                    all_created_tasks.add(future)

                if not tier_futures:
                    continue

                done, pending = await asyncio.wait(
                    tier_futures.keys(), return_when=asyncio.FIRST_COMPLETED
                )

                for task in done:
                    if task.exception():
                        # Fail fast
                        task.result()

                # If we are here, all tasks in `done` are successful.
                # Wait for the rest of the tier to complete.
                if pending:
                    await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)

                # All tasks in the tier are done, store results.
                for future, task_name in tier_futures.items():
                    self.result._add_result(task_name, future.result())

        except Exception:
            for task in all_created_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*all_created_tasks, return_exceptions=True)
            raise
        finally:
            if self._executor:
                self._executor.shutdown(wait=True)

    def do(
        self,
        arg: Optional[Union[Iterable[Any], Callable[..., Any], str]] = None,
        *,
        retries: int = 0,
        timeout: Optional[float] = None,
        workers: Optional[int] = None,
        limit_per_minute: Optional[int] = None,
    ) -> Callable[..., Any]:
        """
        Decorator to register a task.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            task_name = func.__name__
            if hasattr(WoveResult, task_name):
                raise NameError(
                    f"Task name '{task_name}' conflicts with a built-in "
                    "attribute of the WoveResult object and is not allowed."
                )

            map_source = None if callable(arg) else arg
            if (
                workers is not None or limit_per_minute is not None
            ) and map_source is None:
                raise ValueError(
                    "The 'workers' and 'limit_per_minute' parameters can only be used with "
                    "mapped tasks (e.g., @w.do(iterable, ...))."
                )

            final_params = {
                "func": func,
                "map_source": map_source,
                "retries": retries,
                "timeout": timeout,
                "workers": workers,
                "limit_per_minute": limit_per_minute,
            }

            if func.__name__ in self._tasks:
                parent_params = self._tasks[func.__name__]
                if final_params["retries"] == 0:
                    final_params["retries"] = parent_params.get("retries", 0)
                if final_params["timeout"] is None:
                    final_params["timeout"] = parent_params.get("timeout")
                if final_params["workers"] is None:
                    final_params["workers"] = parent_params.get("workers")
                if final_params["limit_per_minute"] is None:
                    final_params["limit_per_minute"] = parent_params.get(
                        "limit_per_minute"
                    )

            self._tasks[func.__name__] = final_params
            if func.__name__ not in self.result._definition_order:
                self.result._definition_order.append(func.__name__)
            return func

        if callable(arg):
            return decorator(arg)
        else:
            return decorator

    async def _merge(
        self, func: Callable[..., Any], iterable: Optional[Iterable[Any]] = None
    ) -> Any:
        # ... (implementation unchanged)
        pass

import asyncio
import inspect
from collections import OrderedDict, deque
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Type

from .helpers import sync_to_async
from .result import WoveResult


class WoveContextManager:
    """
    The core context manager that discovers, orchestrates, and executes tasks
    defined within an `async with weave()` block.

    It builds a dependency graph of tasks based on their function signatures,
    sorts them topologically, and executes them with maximum concurrency
    while respecting dependencies. It handles both `async` and synchronous
    functions, running the latter in a thread pool.
    """

    def __init__(self) -> None:
        """Initializes the context manager, preparing to collect tasks."""
        self._tasks: OrderedDict[str, Callable[..., Any]] = OrderedDict()
        self.result = WoveResult()

    async def __aenter__(self) -> "WoveContextManager":
        """
        Enters the asynchronous context and prepares for task registration.

        Returns:
            The context manager instance itself.
        """
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """
        Exits the context, executes all registered tasks, and populates the
        result container.

        If an exception is raised within the `async with` block, task execution
        is skipped. If a task raises an exception during execution, all other
        running tasks are cancelled, and the exception is propagated.

        Args:
            exc_type: The type of exception raised in the block, if any.
            exc_val: The exception instance raised, if any.
            exc_tb: The traceback for the exception, if any.
        """
        if exc_type:
            # If an exception occurred inside the block, don't execute
            return

        # 1. Build Dependency Graph
        all_task_names = set(self._tasks.keys())
        dependencies: Dict[str, Set[str]] = {
            name: set(inspect.signature(task).parameters.keys()) & all_task_names
            for name, task in self._tasks.items()
        }

        dependents: Dict[str, Set[str]] = {name: set() for name in self._tasks}
        for name, params in dependencies.items():
            for param in params:
                if param in dependents:
                    dependents[param].add(name)

        # 2. Topological Sort to find execution order and detect cycles
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
            unrunnable_tasks = self._tasks.keys() - set(sorted_tasks)
            msg = (
                "Circular dependency detected or missing dependency. Unrunnable tasks: "
                f"{', '.join(sorted(unrunnable_tasks))}"
            )
            raise RuntimeError(msg)

        # 3. Group tasks into execution tiers
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

        # 4. Execute tier by tier
        self.result._definition_order = list(self._tasks.keys())

        for tier in tiers:
            tasks_to_run: List[Coroutine[Any, Any, Any]] = []
            task_names_in_tier: List[str] = []

            for task_name in tier:
                task_func = self._tasks[task_name]
                args = {
                    p: self.result._results[p]
                    for p in dependencies[task_name]
                }

                if not inspect.iscoroutinefunction(task_func):
                    task_func = sync_to_async(task_func)

                coro = task_func(**args)
                tasks_to_run.append(coro)
                task_names_in_tier.append(task_name)

            try:
                # Execute all tasks in the current tier concurrently
                tier_results = await asyncio.gather(*tasks_to_run)

                # Store results
                for task_name, result in zip(task_names_in_tier, tier_results):
                    self.result._results[task_name] = result
            except Exception:
                # asyncio.gather cancels remaining tasks on failure by default.
                # We just need to re-raise the exception that it propagates.
                raise

    def do(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to register a task with the weave context."""
        self._tasks[func.__name__] = func
        return func

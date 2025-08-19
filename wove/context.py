import asyncio
import inspect
from collections import OrderedDict, deque
from contextvars import Token
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Type

from .helpers import sync_to_async
from .result import WoveResult
from .vars import current_weave_context


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
        self._result_container: Optional[WoveResult] = None
        self._reset_token: Optional[Token[Any]] = None

    async def __aenter__(self) -> WoveResult:
        """
        Enters the asynchronous context and prepares for task registration.

        Returns:
            An empty WoveResult container that will be populated with task
            results upon exiting the context.
        """
        self._reset_token = current_weave_context.set(self)
        # The 'as result' variable is initially an empty container
        self._result_container = WoveResult([])
        return self._result_container

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
        if self._reset_token:
            current_weave_context.reset(self._reset_token)
        if exc_type:
            # If an exception occurred inside the block, don't execute
            return

        # 1. Build Dependency Graph
        dependencies: Dict[str, Set[str]] = {
            name: set(inspect.signature(task).parameters.keys())
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

        # We use a copy of in_degree for the sort to not affect the execution logic
        temp_in_degree = in_degree.copy()
        sort_queue = queue.copy()
        while sort_queue:
            task_name = sort_queue.popleft()
            sorted_tasks.append(task_name)
            for dependent in dependents[task_name]:
                temp_in_degree[dependent] -= 1
                if temp_in_degree[dependent] == 0:
                    sort_queue.append(dependent)

        if len(sorted_tasks) != len(self._tasks):
            unrunnable_tasks = self._tasks.keys() - set(sorted_tasks)
            raise RuntimeError(
                "Circular dependency detected. The following tasks form a cycle "
                f"or depend on one: {', '.join(sorted(unrunnable_tasks))}"
            )

        # 3. Execute in Tiers
        running_tasks: Dict[str, asyncio.Task[Any]] = {}
        task_keys = list(self._tasks.keys())
        final_results = WoveResult(task_keys)
        while queue or running_tasks:
            # Start all tasks with met dependencies
            while queue:
                task_name = queue.popleft()
                task_func = self._tasks[task_name]

                # Gather arguments from already completed tasks
                args = {p: final_results[p] for p in dependencies[task_name]}

                # Wrap synchronous functions to run in a thread pool
                if not inspect.iscoroutinefunction(task_func):
                    task_func = sync_to_async(task_func)
                coro: Coroutine[Any, Any, Any] = task_func(**args)
                running_tasks[task_name] = asyncio.create_task(coro)
            if not running_tasks:
                break
            # Wait for the next task to complete
            done, pending = await asyncio.wait(
                running_tasks.values(), return_when=asyncio.FIRST_COMPLETED
            )

            # Process completed tasks
            for completed_task in done:
                # Find the name of the completed task
                task_name = next(
                    name for name, task in running_tasks.items() if task == completed_task
                )

                try:
                    result = completed_task.result()
                    final_results._set_result(task_name, result)
                except Exception as e:
                    # If one task fails, cancel the rest and re-raise
                    for p in pending:
                        p.cancel()
                    raise e

                del running_tasks[task_name]
                # Decrement in-degree for dependents and add to queue if ready
                for dependent in dependents[task_name]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Transfer final results to the user-facing container
        if self._result_container:
            self._result_container._definition_order = task_keys
            for name in task_keys:
                if name in final_results._results:
                    self._result_container._set_result(name, final_results[name])

    def _register_task(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Called by the @do decorator to register a task."""
        self._tasks[func.__name__] = func
        return func

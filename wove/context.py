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
        self._result_container = WoveResult()
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
            msg = ("Circular dependency detected or missing dependency. Unrunnable tasks: "
                f"{', '.join(sorted(unrunnable_tasks))}")
            raise RuntimeError(msg)
            
        # 3. Execute in Tiers
        running_tasks: Dict[asyncio.Task[Any], str] = {}
        completed_results: Dict[str, Any] = {}
        if self._result_container:
            self._result_container._definition_order = list(self._tasks.keys())
        
        while queue or running_tasks:
            # Start all tasks with met dependencies
            while queue:
                task_name = queue.popleft()
                task_func = self._tasks[task_name]
                args = {p: completed_results[p] for p in dependencies[task_name]}
                
                if not inspect.iscoroutinefunction(task_func):
                    task_func = sync_to_async(task_func)
                coro: Coroutine[Any, Any, Any] = task_func(**args)
                task = asyncio.create_task(coro)
                running_tasks[task] = task_name
            if not running_tasks:
                break
            
            # Wait for the next task to complete
            print(f"DEBUG: Awaiting tasks: {[name for name in running_tasks.values()]}") # Temporary debug print
            done, pending = await asyncio.wait(
                set(running_tasks.keys()), return_when=asyncio.FIRST_COMPLETED
            )
            print(f"DEBUG: Done tasks: {[running_tasks[t] for t in done]}") # Temporary debug print
            # Process completed tasks
            for completed_task in done:
                task_name = running_tasks[completed_task]
                try:
                    result = completed_task.result()
                    completed_results[task_name] = result
                except Exception as e:
                    # If one task fails, cancel the rest and re-raise
                    for p in pending:
                        p.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)
                    raise e
                del running_tasks[completed_task]
                # Decrement in-degree for dependents and add to queue if ready
                for dependent in dependents.get(task_name, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        # 4. Populate final results
        if self._result_container:
            self._result_container._results = completed_results
    def _register_task(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Called by the @do decorator to register a task."""
        self._tasks[func.__name__] = func
        return func

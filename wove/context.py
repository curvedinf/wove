import asyncio
import inspect
from collections import OrderedDict, deque
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Type, Union, Iterable
from .helpers import sync_to_async
from .result import WoveResult
class WoveContextManager:
    """
    The core context manager that discovers, orchestrates, and executes tasks
    defined within an `async with weave()` block.
    It builds a dependency graph of tasks, sorts them topologically, and executes
    them with maximum concurrency while respecting dependencies. It handles both
    `async` and synchronous functions, running the latter in a thread pool.
    """
    def __init__(self) -> None:
        """Initializes the context manager, preparing to collect tasks."""
        self._tasks: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.result = WoveResult()
        self._call_stack: List[str] = []
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
        dependencies: Dict[str, Set[str]] = {}
        for name, task_info in self._tasks.items():
            params = set(inspect.signature(task_info["func"]).parameters.keys())
            if task_info["iterable"] is not None:
                # Mapped task: find the single parameter that isn't another task.
                non_dependency_params = params - all_task_names
                if len(non_dependency_params) != 1:
                    msg = (
                        f"Mapped task '{name}' must have exactly one parameter "
                        "that is not a dependency (to receive items from the iterable). "
                        f"Found {len(non_dependency_params)}: {', '.join(sorted(non_dependency_params))}"
                    )
                    raise TypeError(msg)
                item_param_name = non_dependency_params.pop()
                task_info["item_param"] = item_param_name
                dependencies[name] = params & all_task_names
            else:
                # Normal task
                dependencies[name] = params & all_task_names
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
        all_created_tasks: Set[asyncio.Future[Any]] = set()
        try:
            for tier in tiers:
                tier_tasks: Dict[asyncio.Future[Any], str] = {}
                for task_name in tier:
                    task_info = self._tasks[task_name]
                    task_func = task_info["func"]
                    args = {
                        p: self.result._results[p]
                        for p in dependencies[task_name]
                    }
                    if not inspect.iscoroutinefunction(task_func):
                        task_func = sync_to_async(task_func)
                    
                    if task_info["iterable"] is not None:
                        # Mapped Task: Create a task for each item and gather results.
                        item_param = task_info["item_param"]
                        map_sub_tasks = []
                        for item in task_info["iterable"]:
                            map_args = args.copy()
                            map_args[item_param] = item
                            coro = task_func(**map_args)
                            sub_task = asyncio.create_task(coro)
                            map_sub_tasks.append(sub_task)
                            all_created_tasks.add(sub_task)
                        
                        # For mapped tasks, we gather the sub-tasks. The result is a Future.
                        task = asyncio.gather(*map_sub_tasks)
                    else:
                        # Normal Task: Create a single task from the coroutine.
                        coro = task_func(**args)
                        task = asyncio.create_task(coro)
                    
                    tier_tasks[task] = task_name
                    all_created_tasks.add(task)
                # Wait for tasks in the tier, processing them as they complete
                pending = set(tier_tasks.keys())
                while pending:
                    done, pending = await asyncio.wait(
                        pending, return_when=asyncio.FIRST_COMPLETED
                    )
                    # Check for exceptions in completed tasks
                    for task in done:
                        if task.exception():
                            # If a task fails, raise its exception.
                            # The main `except` block will handle cancellation.
                            task.result()  # This re-raises the exception
                # If the loop completes, all tasks in the tier succeeded.
                # Store their results before moving to the next tier.
                for task, task_name in tier_tasks.items():
                    self.result._add_result(task_name, task.result())
        except Exception:
            # If any task raises an exception, cancel all other running tasks.
            for task in all_created_tasks:
                if not task.done():
                    task.cancel()
            # Wait for all tasks to acknowledge cancellation to ensure cleanup.
            # return_exceptions=True prevents gather from stopping on the first
            # CancelledError.
            await asyncio.gather(*all_created_tasks, return_exceptions=True)
            # Re-raise the original exception.
            raise

    async def _merge(self, func: Callable[..., Any], iterable: Optional[Iterable[Any]] = None) -> Any:
        """
        Dynamically executes a callable from within a task, handling recursion
        and concurrency.
        """
        if len(self._call_stack) > 100:
            raise RecursionError(
                "Merge call depth exceeded 100. A circular `merge` "
                "dependency is likely."
            )

        self._call_stack.append(func.__name__)
        try:
            # Wrap sync functions to be awaitable
            if not inspect.iscoroutinefunction(func):
                func = sync_to_async(func)

            if iterable is not None:
                # Mapped/iterable call. Assumes func takes one argument.
                sub_tasks = [asyncio.create_task(func(item)) for item in iterable]
                results = await asyncio.gather(*sub_tasks)
                return results
            else:
                # Single call. Assumes func takes no arguments.
                result = await func()
                return result
        finally:
            self._call_stack.pop()

    def do(self, arg: Optional[Union[Iterable[Any], Callable[..., Any]]] = None) -> Callable[..., Any]:
        """
        Decorator to register a task. Can be used as `@w.do` for a single task
        or `@w.do(iterable)` to map a task over an iterable.
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            iterable = None if callable(arg) else arg
            self._tasks[func.__name__] = {"func": func, "iterable": iterable}
            self.result._definition_order.append(func.__name__)
            return func
        if callable(arg):
            # Used as @w.do
            return decorator(arg)
        else:
            # Used as @w.do(iterable) or @w.do()
            return decorator

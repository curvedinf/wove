# wove.py
# Beautiful python async orchestration

import asyncio
import inspect
from functools import wraps
from collections import OrderedDict, deque

class WoveResult:
    """
    A container for the results of a weave block.

    Supports dictionary-style access by task name, unpacking in definition order,
    and a `.final` shortcut to the last-defined task's result.
    """
    def __init__(self, definition_order):
        self._results = {}
        self._definition_order = definition_order
        self._is_complete = asyncio.Event()

    def __getitem__(self, key):
        return self._results[key]

    def __iter__(self):
        return (self._results[key] for key in self._definition_order)

    def __len__(self):
        return len(self._results)
    
    @property
    def final(self):
        """Returns the result of the last task defined in the weave block."""
        if not self._definition_order:
            return None
        return self._results[self._definition_order[-1]]

    def _set_result(self, key, value):
        self._results[key] = value

    def _mark_complete(self):
        self._is_complete.set()

    async def _wait_for_key(self, key):
        """Waits until a specific result is available."""
        while key not in self._results:
            await self._is_complete.wait()
            self._is_complete.clear()

class WoveContextManager:
    """
    The core context manager that discovers, orchestrates, and executes tasks.
    """
    def __init__(self):
        self._tasks = OrderedDict()
        self._result_container = None

    def __call__(self):
        # Reset state for a new run
        self._tasks.clear()
        return self

    async def __aenter__(self):
        # The 'as result' variable is initially an empty container
        self._result_container = WoveResult(list(self._tasks.keys()))
        return self._result_container

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # If an exception occurred inside the block, don't execute
            return

        # 1. Build Dependency Graph
        dependencies = {name: set(inspect.signature(task).parameters.keys()) for name, task in self._tasks.items()}
        dependents = {name: set() for name in self._tasks}
        for name, params in dependencies.items():
            for param in params:
                if param in dependents:
                    dependents[param].add(name)

        # 2. Topological Sort to find execution order
        in_degree = {name: len(params) for name, params in dependencies.items()}
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        
        # 3. Execute in Tiers
        running_tasks = {}
        final_results = WoveResult(list(self._tasks.keys()))

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

                coro = task_func(**args)
                running_tasks[task_name] = asyncio.create_task(coro)

            if not running_tasks:
                break

            # Wait for the next task to complete
            done, pending = await asyncio.wait(running_tasks.values(), return_when=asyncio.FIRST_COMPLETED)
            
            # Process completed tasks
            for completed_task in done:
                # Find the name of the completed task
                task_name = next(name for name, task in running_tasks.items() if task == completed_task)
                
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
        for name in self._tasks.keys():
            self._result_container._set_result(name, final_results[name])


    def _register_task(self, func):
        """Called by the @do decorator to register a task."""
        self._tasks[func.__name__] = func
        return func

# --- Public API ---

# The main context manager factory
weave = WoveContextManager()

def do(func):
    """A decorator to mark a function as a concurrent task within a weave block."""
    # This is a placeholder; the real registration happens when weave is active.
    # This implementation detail would require contextvars to be truly robust
    # in complex nested or concurrent scenarios, but for a single active
    # 'weave' instance, this direct approach works.
    try:
        weave._register_task(func)
    except AttributeError:
        raise RuntimeError("The @do decorator can only be used inside an 'async with weave()' block.")
    return func

# --- Helper for non-async Django users ---
def sync_to_async(func):
    """
    A simple wrapper to run a synchronous function in asyncio's default
    thread pool executor. A more robust implementation would use asgiref.
    """
    @wraps(func)
    async def run_in_executor(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    return run_in_executor

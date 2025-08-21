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
        self._merge_token = None
        self._executor_token = None

        # Seed the graph with initial values.
        for name, value in initial_values.items():
            if hasattr(WoveResult, name):
                raise NameError(
                    f"Initial value name '{name}' conflicts with a built-in "
                    "attribute of the WoveResult object and is not allowed."
                )
            self.result._add_result(name, value)
            self._tasks[name] = {"func": lambda: value, "map_source": None, "seed": True}

        if parent_weave:
            # If a class is passed, instantiate it. If an instance is passed, use it directly.
            instance_to_load = parent_weave() if inspect.isclass(parent_weave) else parent_weave
            self._load_from_parent(instance_to_load)

    def _load_from_parent(self, parent_weave_instance: "Weave") -> None:
        """Inspects a Weave class and pre-populates the tasks from the given instance."""
        # Inspect the class of the instance to find the functions with metadata
        for name, member in inspect.getmembers(type(parent_weave_instance), inspect.isfunction):
            if hasattr(member, "_wove_task_info"):
                task_info = member._wove_task_info
                # Bind the function to the specific instance that was passed in
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
        self._merge_token = merge_context.set(self._merge)
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
        """Prints a detailed execution plan and dependency report."""
        print("\n--- Wove Debug Report ---")

        sorted_tasks = self.execution_plan.get("sorted_tasks", [])
        seed_names = {k for k, v in self._tasks.items() if v.get('seed')}
        executable_tasks = [t for t in sorted_tasks if t not in seed_names]

        print(f"Detected Tasks ({len(executable_tasks)}):")
        for task_name in executable_tasks:
            print(f"  • {task_name}")

        print("\nDependency Graph:")
        for task_name in executable_tasks:
            deps = self.execution_plan.get("dependencies", {}).get(task_name, set())
            deps -= seed_names
            deps_str = f"Dependencies: {', '.join(deps) or 'None'}"

            dependents = self.execution_plan.get("dependents", {}).get(task_name, set())
            dependents_str = f"Dependents:   {', '.join(dependents) or 'None'}"
            print(f"  • {task_name}\n    {deps_str}\n    {dependents_str}")

        print("\nExecution Plan:")
        tiers = self.execution_plan.get("tiers", [])
        if not any(any(t in executable_tasks for t in tier) for tier in tiers):
            print("  - No tasks to execute.")
        else:
            for i, tier in enumerate(tiers):
                executable_in_tier = [t for t in tier if t in executable_tasks]
                if executable_in_tier:
                    print(f"  - Tier {i + 1}: {', '.join(executable_in_tier)}")

        print("\n--- Starting Execution ---")
        for task_name in executable_tasks:
            task_info = self._tasks[task_name]
            original_func = task_info['func']
            while isinstance(original_func, functools.partial):
                original_func = original_func.func
            kind = "async" if inspect.iscoroutinefunction(original_func) else "sync"

            map_source = task_info.get("map_source")
            map_str = ""
            if map_source:
                source_iterable = self.result._results.get(map_source) if isinstance(map_source, str) else map_source
                if isinstance(source_iterable, (list, tuple, set)):
                    map_str = f" [mapped over {len(source_iterable)} items]"
                else:
                    map_str = f" [map over: {map_source if isinstance(map_source, str) else 'iterable'}]"

            print(f"- {task_name} ({kind}){map_str}")

        print("--- End Report ---\n")

    async def _retry_timeout_wrapper(
        self, task_name: str, task_func: Callable, args: Dict
    ) -> Any:
        task_info = self._tasks[task_name]
        retries = task_info.get("retries", 0)
        timeout = task_info.get("timeout")
        last_exception = None
        start_time = time.monotonic()
        try:
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
        finally:
            end_time = time.monotonic()
            self.result._add_timing(task_name, end_time - start_time)

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        if exc_type:
            # If the context exits with an exception from user code, cancel tasks.
            if self._executor:
                self._executor.shutdown(wait=False)
            return

        all_created_tasks: Set[asyncio.Future] = set()
        try:
            # This outer try...except is to catch CancelledError and allow it
            # to be handled gracefully by the cleanup logic in `finally`.
            try:
                self._build_graph_and_plan()
            except (NameError, TypeError, RuntimeError) as e:
                for task_name in self._tasks:
                    if not task_name in self.result._results: # Don't overwrite seed values
                        self.result._add_error(task_name, e)
                return # Stop execution

            if self._debug:
                self._print_debug_report()

            tiers = self.execution_plan["tiers"]
            dependencies = self.execution_plan["dependencies"]
            dependents = self.execution_plan["dependents"]

            globally_failed_tasks: Set[str] = set()
            # Semaphore for each task that defines a `workers` limit
            semaphores: Dict[str, asyncio.Semaphore] = {}

            for tier in tiers:
                tier_futures: Dict[str, Union[asyncio.Future, List[asyncio.Future]]] = {}
                tasks_in_tier_to_run = [t for t in tier if t not in globally_failed_tasks]

                for task_name in tasks_in_tier_to_run:
                    task_info = self._tasks[task_name]
                    task_func = task_info["func"]
                    task_deps = dependencies.get(task_name, set())
                    map_source_name = task_info.get("map_source") if isinstance(task_info.get("map_source"), str) else None
                    args = {p: self.result._results[p] for p in task_deps if p != map_source_name}

                    if not inspect.iscoroutinefunction(task_func):
                        task_func = sync_to_async(task_func)

                    map_source = task_info.get("map_source")
                    if map_source is not None:
                        # Mapped task
                        item_param = task_info.get("item_param")
                        iterable_source = self.result._results.get(map_source_name) if map_source_name else map_source

                        # Handle non-iterable map source as a recoverable error
                        if not isinstance(iterable_source, Iterable):
                            e = TypeError(f"result of type '{type(iterable_source).__name__}' is not iterable")
                            self.result._add_error(task_name, e)
                            # Manually trigger failure propagation
                            tasks_to_fail = deque([task_name])
                            processed_for_failure = {task_name}
                            while tasks_to_fail:
                                current_failed_task = tasks_to_fail.popleft()
                                globally_failed_tasks.add(current_failed_task)
                                for dep in dependents.get(current_failed_task, []):
                                    if dep not in processed_for_failure:
                                        self.result._add_error(dep, e)
                                        tasks_to_fail.append(dep)
                                        processed_for_failure.add(dep)
                            continue # Skip to the next task in the tier

                        workers = task_info.get("workers")
                        if workers and task_name not in semaphores:
                            semaphores[task_name] = asyncio.Semaphore(workers)

                        limit_per_minute = task_info.get("limit_per_minute")
                        delay = 60.0 / limit_per_minute if limit_per_minute else 0

                        async def mapped_task_runner(item, index):
                            # Stagger start times for throttling
                            if limit_per_minute and index > 0:
                                await asyncio.sleep(index * delay)

                            semaphore = semaphores.get(task_name)
                            if semaphore:
                                async with semaphore:
                                    return await self._retry_timeout_wrapper(task_name, task_func, {**args, item_param: item})
                            return await self._retry_timeout_wrapper(task_name, task_func, {**args, item_param: item})

                        mapped_futures = [asyncio.create_task(mapped_task_runner(item, i)) for i, item in enumerate(iterable_source)]
                        tier_futures[task_name] = mapped_futures
                        all_created_tasks.update(mapped_futures)
                    else:
                        # Regular task
                        future = asyncio.create_task(self._retry_timeout_wrapper(task_name, task_func, args))
                        tier_futures[task_name] = future
                        all_created_tasks.add(future)

                if not tier_futures:
                    continue

                # Wait for all tasks created in this tier to complete
                current_tier_futures = [f for flist in tier_futures.values() for f in (flist if isinstance(flist, list) else [flist])]

                if not current_tier_futures:
                    # Handle cases like mapping over an empty list
                    for task_name in tasks_in_tier_to_run:
                        if isinstance(tier_futures.get(task_name), list):
                            self.result._add_result(task_name, [])
                    continue

                done, pending = await asyncio.wait(current_tier_futures, return_when=asyncio.FIRST_COMPLETED)

                exception_found = None
                # Prioritize non-cancellation exceptions as the root cause
                for f in done:
                    exc = f.exception()
                    if exc and not isinstance(exc, asyncio.CancelledError):
                        exception_found = exc
                        break

                # If no "real" exception was found, the first exception (likely a CancelledError) will do.
                if not exception_found:
                    for f in done:
                        if f.exception():
                            exception_found = f.exception()
                            break

                if exception_found:
                    # Cancel pending tasks in this tier
                    for p in pending:
                        p.cancel()
                    # Wait for cancellations to propagate
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)

                if exception_found:
                    print(f"DEBUG: Exception found: {type(exception_found)} {exception_found}")
                    # The whole weave fails. Find the task that caused it.
                    source_of_failure = None
                    def _exc_match(e1, e2):
                        if e1 is None or e2 is None: return False
                        return type(e1) is type(e2) and str(e1) == str(e2)

                    for task_name, f_or_list in tier_futures.items():
                        print(f"DEBUG: Checking task {task_name}")
                        if isinstance(f_or_list, list):
                            for i, f in enumerate(f_or_list):
                                try:
                                    exc = f.exception()
                                    print(f"DEBUG:  - subtask {i} exc: {type(exc)} {exc}")
                                    if _exc_match(exc, exception_found):
                                        source_of_failure = task_name
                                        break
                                except asyncio.CancelledError:
                                    print(f"DEBUG:  - subtask {i} was cancelled.")
                        else:
                            try:
                                exc = f_or_list.exception()
                                print(f"DEBUG:  - single task exc: {type(exc)} {exc}")
                                if _exc_match(exc, exception_found):
                                    source_of_failure = task_name
                            except asyncio.CancelledError:
                                    print(f"DEBUG:  - single task {task_name} was cancelled.")
                        if source_of_failure:
                            break

                    print(f"DEBUG: Source of failure found: {source_of_failure}")

                    # Mark the source task and its dependents as failed.
                    if source_of_failure:
                        self.result._add_error(source_of_failure, exception_found)
                        tasks_to_fail = deque([source_of_failure])
                        processed_for_failure = {source_of_failure}
                        while tasks_to_fail:
                            current_failed_task = tasks_to_fail.popleft()
                            globally_failed_tasks.add(current_failed_task)
                            for dep in dependents.get(current_failed_task, []):
                                if dep not in processed_for_failure:
                                    self.result._add_error(dep, exception_found)
                                    tasks_to_fail.append(dep)
                                    processed_for_failure.add(dep)
                    # After handling the exception, skip processing results for this tier.
                    continue

                # No exceptions, wait for the rest of the tier and process results
                if pending:
                    await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)

                for task_name in tasks_in_tier_to_run:
                    if task_name not in tier_futures: continue
                    future_or_list = tier_futures[task_name]

                    try:
                        if isinstance(future_or_list, list):
                            results = [f.result() for f in future_or_list]
                            if task_name not in self.result.timings: # Record timing for the whole map
                                self.result._add_timing(task_name, 0) # Placeholder
                            self.result._add_result(task_name, results)
                        else:
                            self.result._add_result(task_name, future_or_list.result())
                    except asyncio.CancelledError:
                        # This isn't a task failure, it's a result of another task failing.
                        # The task will just not have a result. The original error is already propagated.
                        pass
                    except Exception as e:
                        self.result._add_error(task_name, e)
                        tasks_to_fail = deque([task_name])
                        processed_for_failure = {task_name}
                        while tasks_to_fail:
                            current_failed_task = tasks_to_fail.popleft()
                            globally_failed_tasks.add(current_failed_task)
                            for dep in dependents.get(current_failed_task, []):
                                if dep not in processed_for_failure:
                                    self.result._add_error(dep, e)
                                    tasks_to_fail.append(dep)
                                    processed_for_failure.add(dep)

        except asyncio.CancelledError:
            # The weave was cancelled externally.
            pass
        except (NameError, TypeError, RuntimeError) as e:
            # Graph-building errors should fail fast.
            raise e
        finally:
            # Final cleanup
            for task in all_created_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*all_created_tasks, return_exceptions=True)

            if self._executor:
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        await loop.run_in_executor(None, self._executor.shutdown)
                except RuntimeError:
                    pass # Loop is already closed

            if self._executor_token:
                executor_context.reset(self._executor_token)
            if self._merge_token:
                merge_context.reset(self._merge_token)

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
        """
        Dynamically executes a callable from within a Wove task, integrating
        its result into the dependency graph.
        """
        # Simple recursion guard
        if len(self._call_stack) > 100:
            raise RecursionError("Merge call depth exceeded 100")

        # Get the name of the function for the call stack
        func_name = getattr(func, '__name__', 'anonymous_callable')
        self._call_stack.append(func_name)

        try:
            # If the provided function is synchronous, wrap it to run in the executor
            if not inspect.iscoroutinefunction(getattr(func, 'func', func)):
                func = sync_to_async(func)

            if iterable is None:
                # Single execution
                res = await func()
                if inspect.iscoroutine(res):
                    res = await res
                return res
            else:
                # Mapped execution
                async def run_and_await(item):
                    res = await func(item)
                    if inspect.iscoroutine(res):
                        res = await res
                    return res

                items = list(iterable)
                tasks = [asyncio.create_task(run_and_await(item)) for item in items]
                return await asyncio.gather(*tasks)
        finally:
            self._call_stack.pop()

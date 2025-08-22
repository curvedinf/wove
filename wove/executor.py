import asyncio
import time
from collections import deque
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Set,
    Union,
)

from .helpers import sync_to_async


async def retry_timeout_wrapper(
    task_name: str, task_func: Callable, args: Dict, tasks: Dict, result: Any
) -> Any:
    task_info = tasks[task_name]
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
            except asyncio.CancelledError:
                result._add_cancelled(task_name)
                raise
            except (Exception, asyncio.TimeoutError) as e:
                last_exception = e
        raise last_exception from None
    finally:
        end_time = time.monotonic()
        result._add_timing(task_name, end_time - start_time)


async def execute_plan(
    execution_plan: Dict[str, Any],
    tasks: Dict,
    result: Any,
    context: Any,
):
    all_created_tasks: Set[asyncio.Future] = set()
    try:
        tiers = execution_plan["tiers"]
        dependencies = execution_plan["dependencies"]
        dependents = execution_plan["dependents"]

        globally_failed_tasks: Set[str] = set()
        semaphores: Dict[str, asyncio.Semaphore] = {}

        for i, tier in enumerate(tiers):
            tier_pre_execution_start = time.monotonic()
            tier_futures: Dict[str, Union[asyncio.Future, List[asyncio.Future]]] = {}
            tasks_in_tier_to_run = [t for t in tier if t not in globally_failed_tasks]

            for task_name in tasks_in_tier_to_run:
                task_info = tasks[task_name]
                task_func = task_info["func"]
                task_deps = dependencies.get(task_name, set())
                map_source_name = task_info.get("map_source") if isinstance(task_info.get("map_source"), str) else None
                args = {p: result._results[p] for p in task_deps if p != map_source_name}

                if not asyncio.iscoroutinefunction(task_func):
                    task_func = sync_to_async(task_func)

                map_source = task_info.get("map_source")
                if map_source is not None:
                    item_param = task_info.get("item_param")
                    iterable_source = result._results.get(map_source_name) if map_source_name else map_source

                    if not isinstance(iterable_source, Iterable):
                        e = TypeError(f"result of type '{type(iterable_source).__name__}' is not iterable")
                        result._add_error(task_name, e)
                        tasks_to_fail = deque([task_name])
                        processed_for_failure = {task_name}
                        while tasks_to_fail:
                            current_failed_task = tasks_to_fail.popleft()
                            globally_failed_tasks.add(current_failed_task)
                            for dep in dependents.get(current_failed_task, []):
                                if dep not in processed_for_failure:
                                    result._add_error(dep, e)
                                    tasks_to_fail.append(dep)
                                    processed_for_failure.add(dep)
                        continue

                    workers = task_info.get("workers")
                    if workers and task_name not in semaphores:
                        semaphores[task_name] = asyncio.Semaphore(workers)

                    limit_per_minute = task_info.get("limit_per_minute")
                    delay = 60.0 / limit_per_minute if limit_per_minute else 0

                    async def mapped_task_runner(item, index):
                        if limit_per_minute and index > 0:
                            await asyncio.sleep(index * delay)

                        semaphore = semaphores.get(task_name)
                        if semaphore:
                            async with semaphore:
                                return await retry_timeout_wrapper(task_name, task_func, {**args, item_param: item}, tasks, result)
                        return await retry_timeout_wrapper(task_name, task_func, {**args, item_param: item}, tasks, result)

                    mapped_futures = [asyncio.create_task(mapped_task_runner(item, i)) for i, item in enumerate(iterable_source)]
                    tier_futures[task_name] = mapped_futures
                    all_created_tasks.update(mapped_futures)
                else:
                    future = asyncio.create_task(retry_timeout_wrapper(task_name, task_func, args, tasks, result))
                    tier_futures[task_name] = future
                    all_created_tasks.add(future)

            tier_execution_start = time.monotonic()
            result._add_timing(f"tier_{i+1}_pre_execution", tier_execution_start - tier_pre_execution_start)

            if not tier_futures:
                continue

            current_tier_futures = [f for flist in tier_futures.values() for f in (flist if isinstance(flist, list) else [flist])]

            if not current_tier_futures:
                for task_name in tasks_in_tier_to_run:
                    if isinstance(tier_futures.get(task_name), list):
                        result._add_result(task_name, [])
                tier_post_execution_start = time.monotonic()
                result._add_timing(f"tier_{i+1}_execution", tier_post_execution_start - tier_execution_start)
                result._add_timing(f"tier_{i+1}_post_execution", 0)
                continue

            done, pending = await asyncio.wait(current_tier_futures, return_when=asyncio.FIRST_EXCEPTION)

            exception_found = None
            for f in done:
                exc = f.exception()
                if exc and not isinstance(exc, asyncio.CancelledError):
                    exception_found = exc
                    break

            if not exception_found:
                for f in done:
                    if f.exception():
                        exception_found = f.exception()
                        break

            if exception_found:
                # Build a reverse mapping from future to task name for efficient lookup.
                future_to_task_name = {
                    f: name
                    for name, f_or_list in tier_futures.items()
                    for f in (f_or_list if isinstance(f_or_list, list) else [f_or_list])
                }
                for p in pending:
                    p.cancel()
                    task_name = future_to_task_name.get(p)
                    # For mapped tasks, we only want to add the parent task once.
                    if task_name and task_name not in result.cancelled:
                        result._add_cancelled(task_name)

                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)

                source_of_failure = None
                def _exc_match(e1, e2):
                    if e1 is None or e2 is None: return False
                    return type(e1) is type(e2) and str(e1) == str(e2)

                for task_name, f_or_list in tier_futures.items():
                    if isinstance(f_or_list, list):
                        for i, f in enumerate(f_or_list):
                            if _exc_match(f.exception(), exception_found):
                                source_of_failure = task_name
                                break
                    else:
                        if _exc_match(f_or_list.exception(), exception_found):
                            source_of_failure = task_name
                    if source_of_failure:
                        break

                if source_of_failure:
                    result._add_error(source_of_failure, exception_found)
                    tasks_to_fail = deque([source_of_failure])
                    processed_for_failure = {source_of_failure}
                    while tasks_to_fail:
                        current_failed_task = tasks_to_fail.popleft()
                        globally_failed_tasks.add(current_failed_task)
                        for dep in dependents.get(current_failed_task, []):
                            if dep not in processed_for_failure:
                                result._add_error(dep, exception_found)
                                tasks_to_fail.append(dep)
                                processed_for_failure.add(dep)
                continue

            if pending:
                await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)

            tier_post_execution_start = time.monotonic()
            result._add_timing(f"tier_{i+1}_execution", tier_post_execution_start - tier_execution_start)

            for task_name in tasks_in_tier_to_run:
                if task_name not in tier_futures:
                    continue
                future_or_list = tier_futures[task_name]

                try:
                    if isinstance(future_or_list, list):
                        results = []
                        for f in future_or_list:
                            try:
                                results.append(f.result())
                            except asyncio.CancelledError:
                                result._add_cancelled(task_name)
                        if task_name not in result.timings:
                            result._add_timing(task_name, 0)
                        result._add_result(task_name, results)
                    else:
                        result._add_result(task_name, future_or_list.result())
                except asyncio.CancelledError:
                    result._add_cancelled(task_name)
                except Exception as e:
                    result._add_error(task_name, e)
                    tasks_to_fail = deque([task_name])
                    processed_for_failure = {task_name}
                    while tasks_to_fail:
                        current_failed_task = tasks_to_fail.popleft()
                        globally_failed_tasks.add(current_failed_task)
                        for dep in dependents.get(current_failed_task, []):
                            if dep not in processed_for_failure:
                                result._add_error(dep, e)
                                tasks_to_fail.append(dep)
                                processed_for_failure.add(dep)

            tier_post_execution_end = time.monotonic()
            result._add_timing(f"tier_{i+1}_post_execution", tier_post_execution_end - tier_post_execution_start)
    finally:
        for task in all_created_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*all_created_tasks, return_exceptions=True)

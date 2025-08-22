import functools
import inspect
from typing import (
    Any,
    Dict,
)


def print_debug_report(execution_plan: Dict[str, Any], tasks: Dict, result: Dict) -> None:
    """Prints a detailed execution plan and dependency report."""
    print("\n--- Wove Debug Report ---")

    sorted_tasks = execution_plan.get("sorted_tasks", [])
    seed_names = {k for k, v in tasks.items() if v.get('seed')}
    executable_tasks = [t for t in sorted_tasks if t not in seed_names]

    print(f"Detected Tasks ({len(executable_tasks)}):")
    for task_name in executable_tasks:
        print(f"  • {task_name}")

    print("\nDependency Graph:")
    for task_name in executable_tasks:
        deps = execution_plan.get("dependencies", {}).get(task_name, set())
        deps -= seed_names
        deps_str = f"Dependencies: {', '.join(deps) or 'None'}"

        dependents = execution_plan.get("dependents", {}).get(task_name, set())
        dependents_str = f"Dependents:   {', '.join(dependents) or 'None'}"
        print(f"  • {task_name}\n    {deps_str}\n    {dependents_str}")

    print("\nExecution Plan:")
    tiers = execution_plan.get("tiers", [])
    if not any(any(t in executable_tasks for t in tier) for tier in tiers):
        print("  - No tasks to execute.")
    else:
        for i, tier in enumerate(tiers):
            executable_in_tier = [t for t in tier if t in executable_tasks]
            if executable_in_tier:
                print(f"  - Tier {i + 1}: {', '.join(executable_in_tier)}")

    print("\n--- Starting Execution ---")
    for task_name in executable_tasks:
        task_info = tasks[task_name]
        original_func = task_info['func']
        while isinstance(original_func, functools.partial):
            original_func = original_func.func
        kind = "async" if inspect.iscoroutinefunction(original_func) else "sync"

        map_source = task_info.get("map_source")
        map_str = ""
        if map_source:
            source_iterable = result.get(map_source) if isinstance(map_source, str) else map_source
            if isinstance(source_iterable, (list, tuple, set)):
                map_str = f" [mapped over {len(source_iterable)} items]"
            else:
                map_str = f" [map over: {map_source if isinstance(map_source, str) else 'iterable'}]"

        print(f"- {task_name} ({kind}){map_str}")

    print("--- End Report ---\n")

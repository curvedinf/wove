import inspect
from collections import deque
from typing import (
    Any,
    Dict,
    List,
    Set,
)

from .errors import UnresolvedSignatureError


def build_graph_and_plan(tasks: Dict, result: Dict, definition_order: List[str]) -> Dict[str, Any]:
    """
    Builds the dependency graph, sorts it topologically, and creates an
    execution plan in tiers.
    """
    all_task_names = set(tasks.keys())
    dependencies: Dict[str, Set[str]] = {}
    for name, task_info in tasks.items():
        # Seed values are not real tasks, they have no dependencies.
        is_seed = name in result and not hasattr(task_info["func"], '_wove_task_info') and name not in definition_order
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
        else:
            unresolved_params = params - all_task_names
            if unresolved_params:
                available = f"Available dependencies: {', '.join(all_task_names)}"
                raise UnresolvedSignatureError(
                    f"Task '{name}' has unresolved dependencies: {', '.join(unresolved_params)}. {available}"
                )
        dependencies[name] = task_dependencies

    dependents: Dict[str, Set[str]] = {name: set() for name in tasks}
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
    if len(sorted_tasks) != len(tasks):
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

    return {
        "dependencies": dependencies,
        "dependents": dependents,
        "tiers": tiers,
        "sorted_tasks": sorted_tasks,
    }

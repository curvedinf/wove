"""
Example: Chained Dynamic Mapping
This script demonstrates how to chain mapped tasks, where one mapped task
operates on the results of a preceding mapped task.

Wove automatically handles the dependency, ensuring that `task_b` (the first
mapped task) fully completes before starting the `task_c` sub-tasks.
"""
import asyncio
from wove import weave

async def main():
    """Demonstrates chaining one mapped task over the result of another."""
    print("--- Running Chained Dynamic Mapping Example ---")
    async with weave() as w:
        # 1. This task generates the initial data.
        @w.do
        async def task_a():
            print("-> task_a: Generating initial data [1, 2, 3]...")
            await asyncio.sleep(0.01)
            return [1, 2, 3]

        # 2. This task is mapped over the result of `task_a`.
        # It runs an instance of `task_b` for each item in [1, 2, 3].
        @w.do("task_a")
        def task_b(item):
            # This is a synchronous function, so print statements are safe.
            print(f"  -> task_b: Processing item {item} -> {item * 10}")
            return item * 10

        # 3. This task is mapped over the result of `task_b`.
        # The result of `task_b` will be [10, 20, 30]. `task_c` will
        # be mapped over that list.
        @w.do("task_b")
        async def task_c(item):
            print(f"    -> task_c: Processing item {item} -> {item + 1}")
            await asyncio.sleep(0.01)
            return item + 1

        # 4. This final task collects all results for display.
        @w.do
        def summary(task_a, task_b, task_c):
            return {
                "initial_data": task_a,
                "first_mapping": task_b,
                "second_mapping": task_c,
            }

    print("\n--- Results ---")
    print(f"Initial data from task_a: {w.result['task_a']}")
    print(f"First mapping (task_b results): {w.result['task_b']}")
    print(f"Second mapping (task_c results): {w.result['task_c']}")
    print(f"\nFinal Summary: {w.result.final}")

    # Verify the results
    assert w.result["task_a"] == [1, 2, 3]
    assert w.result["task_b"] == [10, 20, 30]
    assert w.result["task_c"] == [11, 21, 31]

    print("\n--- Chained Dynamic Mapping Example Finished ---")


if __name__ == "__main__":
    asyncio.run(main())

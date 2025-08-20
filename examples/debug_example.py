"""
Example: Debugging and Introspection
This script demonstrates how to use Wove's debug mode to inspect the
dependency graph and execution plan of your tasks.
To enable debug mode, simply pass `debug=True` to the `weave` context manager.
Wove will print a detailed, color-coded report to the console *before*
executing the tasks.
This example also shows how to programmatically access the execution plan and
task timings after the `weave` block completes.
"""

import asyncio
import time
from wove import weave


async def run_debug_example():
    """
    Runs a simple diamond-shaped dependency graph with debug mode enabled.
    """
    print("--- Running Debugging and Introspection Example ---")

    # When debug=True, a full report is printed to the console.
    async with weave(debug=True) as w:
        # Tier 1: This task runs first.
        @w.do
        async def initial_data():
            print(" -> Running initial_data...")
            await asyncio.sleep(0.02)
            print(" <- Finished initial_data.")
            return {"value": 10}

        # Tier 2: These two tasks depend on initial_data and run concurrently.
        # One is async, one is sync, to show the different debug tags.
        @w.do
        async def process_a(initial_data):
            print(" -> Running process_a...")
            await asyncio.sleep(0.05)
            print(" <- Finished process_a.")
            return initial_data["value"] * 2

        @w.do
        def process_b(initial_data):
            print(" -> Running process_b...")
            time.sleep(0.03)  # Sync blocking task
            print(" <- Finished process_b.")
            return initial_data["value"] + 5

        # Tier 3: This task depends on both process_a and process_b.
        @w.do
        def combine_results(process_a, process_b):
            print(" -> Running combine_results...")
            print(" <- Finished combine_results.")
            return {"a": process_a, "b": process_b}

    # --- Programmatic Access to Execution Data ---
    print("\n--- Programmatic Introspection ---")

    # The execution_plan is available on the context manager instance
    # after the block completes. It contains the full dependency graph and tiers.
    print("\nExecution Plan (from w.execution_plan):")
    # A real application might json.dumps this for logging.
    print(f"  - Tiers: {w.execution_plan['tiers']}")
    print(
        f"  - Dependencies of 'combine_results': {w.execution_plan['dependencies']['combine_results']}"
    )

    # The `w.result.timings` dictionary stores the execution duration of each task.
    # This is invaluable for identifying performance bottlenecks.
    print("\nTask Timings (from w.result.timings):")
    for task_name, duration in w.result.timings.items():
        print(f"  - {task_name}: {duration:.4f}s")

    print(f"\nFinal result: {w.result.final}")

    # --- Verification ---
    assert w.result.final == {"a": 20, "b": 15}
    assert "initial_data" in w.result.timings
    assert "process_a" in w.result.timings
    assert "process_b" in w.result.timings
    assert "combine_results" in w.result.timings
    # Note: Tiers can have varying order for items at the same level
    assert w.execution_plan["tiers"][0] == ["initial_data"]
    assert set(w.execution_plan["tiers"][1]) == {"process_a", "process_b"}
    assert w.execution_plan["tiers"][2] == ["combine_results"]

    print("\n--- Debugging and Introspection Example Finished ---")


if __name__ == "__main__":
    asyncio.run(run_debug_example())

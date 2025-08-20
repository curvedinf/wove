"""
Example: Dependent Mapped Tasks
This script demonstrates how to map a task over the result of a preceding task.
Wove automatically ensures `f1` completes before starting the mapped `f2` tasks.
"""
import asyncio
from wove import weave

async def main():
    """Demonstrates mapping a task over the result of another task."""
    print("--- Running Dependent Mapped Task Example ---")
    async with weave() as w:
        # 1. This task generates the data we want to map over.
        @w.do
        async def f1():
            print("-> f1: Generating data...")
            await asyncio.sleep(0.01)
            # Using a smaller range for cleaner example output
            data = list(range(10))
            print(f"<- f1: Generated {data}")
            return data

        # 2. This task is mapped over the *result* of `f1`.
        # The `item` parameter receives each value from the list [0, 1, ..., 9].
        # Wove runs an instance of `f2` for each item concurrently.
        @w.do("f1")
        async def f2(item):
            return item * item

        # 3. This task is mapped over the result set of `f2` to demonstrate chaining mapped tasks.
        @w.do("f2")
        async def f3(item):
            return item + 1

        # 4. This final task collects the results from all `f3` executions.
        @w.do
        async def f4(f3):
            print(f"-> f4: Summarizing results from f2: {f3}")
            result = sum(f3)
            print(f"<- f4: Sum is {result}")
            return result

    print(f"\nFinal Result (Sum of squares): {w.result.final}")
    # Verify the result
    expected_sum = sum(x*x+1 for x in range(10))
    assert w.result.final == expected_sum
    print("--- Dependent Mapped Task Example Finished ---")

if __name__ == "__main__":
    asyncio.run(main())

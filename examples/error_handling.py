"""
Example: Error Handling and Task Cancellation
This script demonstrates Wove's behavior when a task raises an exception.
- No new tasks are scheduled.
- All other currently running tasks are cancelled.
- The original exception is propagated out of the `weave` block.
In this example, `failing_task` will raise a `ValueError` after a short
delay. This will cause `long_task`, which is already running, to be
cancelled. The `dependent_task` will never even start because its dependency
fails.
"""

import asyncio
from wove import weave


async def run_error_handling_example():
    """
    Runs the error handling and cancellation example.
    """
    was_cancelled = False
    print("--- Running Error Handling Example ---")
    try:
        async with weave() as w:

            @w.do
            async def long_task():
                nonlocal was_cancelled
                print("-> long_task started, will sleep for 2 seconds...")
                try:
                    await asyncio.sleep(2)  # Simulate a long I/O operation
                except asyncio.CancelledError:
                    was_cancelled = True
                    print("<- long_task was cancelled as expected.")
                    raise
                return "This should not be returned."

            @w.do
            async def failing_task():
                # Let long_task start running first
                await asyncio.sleep(0.1)
                print("!! failing_task is about to raise an exception.")
                raise ValueError("Something went wrong in a task")

            @w.do
            def dependent_task(failing_task):
                # This task will never run because its dependency fails.
                print("xx dependent_task should never run.")
                return "never"
    except ValueError as e:
        print(f"\nSuccessfully caught expected exception: {e}")

    assert was_cancelled, "The long-running task was not cancelled."
    print("--- Error Handling Example Finished ---")


if __name__ == "__main__":
    asyncio.run(run_error_handling_example())

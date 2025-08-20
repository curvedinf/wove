# Wove
Stop wrestling with `asyncio`. Start orchestrating.

Python's `asyncio` is powerful, but it often leads to a tangle of `create_task`, `gather`, and manual result handling. Your business logic gets lost in boilerplate.

Wove frees your code by letting you write simple, clean functions that look synchronous and read top-to-bottom. It automatically discovers their dependencies and executes them with maximum concurrency. It is orchestration without the ceremony.

-   **Why Wove?** Unlike `asyncio.gather`, which needs you to manually build a list of awaitables, Wove infers the execution graph directly from your function signatures. Unlike heavy frameworks like Celery or Airflow, Wove is a zero-dependency, lightweight library for in-process concurrency, perfect for I/O-bound work like API calls and database queries in a single request or script.

## Installation
This project is not yet on PyPI. To install locally for development:
```bash
pip install -e .
```
## Core Concepts
Wove is built on a few simple principles to make async code feel more Pythonic.

-   **Looks Like Normal Python**: You write simple, decorated functions. No manual task objects, no callbacks.
-   **Reads Top-to-Bottom**: The code in a `weave` block is declared in a logical order, but `wove` intelligently determines the optimal *execution* order.
-   **Automatic Parallelism**: Wove builds a dependency graph from your function signatures (e.g., `def task_b(task_a): ...`) and runs independent tasks concurrently.
-   **Minimal Boilerplate**: Get started with just the `async with weave() as w:` context manager and the `@w.do` decorator.
-   **Sync & Async Transparency**: Mix `async def` and `def` functions freely. `wove` automatically runs synchronous functions in a background thread pool to avoid blocking the event loop.
-   **Zero Dependencies**: Wove is pure Python, using only the standard library.

## The Basics
Wove introduces three main tools to manage your workflow:

-   `weave()`: An `async` context manager that creates the execution environment for your tasks.
-   `@w.do`: A decorator that registers a function as a task to be run within the `weave` block.
-   `merge()`: A function to dynamically call and `await` other functions from *inside* a running task.

Here they are in action:
```python
import asyncio
import time
from wove import weave, merge

# A function we can call dynamically. Wove will run this sync
# function in a thread pool to avoid blocking.
def process_data(item: int):
    """A simple synchronous, CPU-bound-style function."""
    print(f"  -> Processing item {item}...")
    time.sleep(0.1) # Simulate work
    return item * item

async def run_example():
    """Demonstrates weave, @w.do, and merge."""
    async with weave() as w:
        # 1. @w.do registers a task. This one runs immediately.
        @w.do
        async def initial_data():
            print("-> Fetching initial data...")
            await asyncio.sleep(0.1)
            return [1, 2, 3]

        # 2. This task depends on `initial_data`. It waits for the
        #    result before running.
        @w.do
        async def dynamic_processing(initial_data):
            print(f"-> Concurrently processing {len(initial_data)} items...")
            # `merge` dynamically calls `process_data` for each item
            # in the list, running them all in parallel.
            results = await merge(process_data, initial_data)
            return results

        # 3. This final task depends on the merged results.
        @w.do
        def summarize(dynamic_processing):
            print("-> Summarizing results...")
            total = sum(dynamic_processing)
            return f"Sum of squares: {total}"

    # Results are available after the block exits via w.result
    print(f"\nFinal Summary: {w.result.final}")
    # Expected output:
    # -> Fetching initial data...
    # -> Concurrently processing 3 items...
    #   -> Processing item 1...
    #   -> Processing item 2...
    #   -> Processing item 3...
    # -> Summarizing results...
    #
    # Final Summary: Sum of squares: 14

if __name__ == "__main__":
    asyncio.run(run_example())
```
## Advanced Features

-   **Task Mapping**: For simple parallel processing over an iterable, `@w.do(iterable)` is a powerful shortcut. The decorated function will be executed concurrently for each item.
    ```python
    ids = [1, 2, 3]
    async with weave() as w:
        @w.do(ids)
        async def fetch_user(user_id):
            # This runs 3 times in parallel
            ... # e.g. return await get_user_from_db(user_id)
    # w.result['fetch_user'] will be a list of 3 user objects
    ```
-   **Error Handling**: If any task raises an exception, Wove halts execution, cancels all other running tasks, and re-raises the original exception from the `async with weave()` block. This ensures predictable state and allows you to use standard `try...except` blocks.

-   **Debugging & Introspection**: Need to see what's going on under the hood?
    -   `async with weave(debug=True) as w:`: Prints a detailed, color-coded execution plan to the console before running.
    -   `w.execution_plan`: After the block, this dictionary contains the full dependency graph and execution tiers.
    -   `w.result.timings`: A dictionary mapping each task name to its execution duration in seconds, perfect for finding bottlenecks.

## More Examples
For more advanced use cases, including API aggregation, ETL pipelines, and complex conditional workflows, see the runnable scripts in the `examples/` directory.
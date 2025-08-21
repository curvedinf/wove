# Wove
Beautiful Python async.
## What is Wove For?
Wove is for running high latency async tasks like web requests and database queries concurrently in the same way as 
asyncio, but with a drastically improved user experience.
Improvements compared to asyncio include:
-   **Looks Like Normal Python**: Parallelism and execution order are implicit. You write simple, decorated functions. No manual task objects, no callbacks.
-   **Reads Top-to-Bottom**: The code in a `weave` block is declared in the order it is executed inline in your code instead of in disjointed functions.
-   **Automatic Parallelism**: Wove builds a dependency graph from your function signatures and runs independent tasks concurrently as soon as possible.
-   **High Visibility**: Wove includes debugging tools that allow you to identify where exceptions and deadlocks occur across parallel tasks, and inspect inputs and outputs at each stage of execution.
-   **Normal Python Data**: Wove's task data looks like normal Python variables because it is. This is because of inherent multithreaded data safety produced in the same way as map-reduce.
-   **Minimal Boilerplate**: Get started with just the `async with weave() as w:` context manager and the `@w.do` decorator.
-   **Sync & Async Transparency**: Mix `async def` and `def` functions freely. `wove` automatically runs synchronous functions in a background thread pool to avoid blocking the event loop.
-   **Zero Dependencies**: Wove is pure Python, using only the standard library and can be integrated into any Python project.
## Installation
Download wove with pip:
```bash
pip install wove
```
## The Basics
Wove can be used in any standard Python script or REPL. It automatically manages the `asyncio` event loop, allowing you to mix `async` and `def` functions without boilerplate. When the `weave` block exits, all tasks are executed based on a dependency graph built from their function signatures.

```python
# Save as example.py and run `python example.py`
# or copy-paste into a Python console.
import time
from wove import weave

# The `weave` block can be used without `async with`.
# Wove will manage the event loop behind the scenes.
with weave() as w:
    # This task takes 1 second to run.
    @w.do
    def magic_number():
        time.sleep(1.0)
        return 42

    # This task also takes 1 second. Wove runs it
    # in parallel with `magic_number` in a background thread.
    @w.do
    def important_text():
        time.sleep(1.0)
        return "The meaning of life"

    # This task depends on the first two. It runs only
    # after both are complete.
    @w.do
    def put_together(important_text, magic_number):
        return f"{important_text} is {magic_number}!"

# The block finishes here, taking ~1 second total.
# Access the result of the final task via `w.result.final`.
print(w.result.final)
# >> The meaning of life is 42!

# Access other task results by name.
print(f"The magic number was {w.result.magic_number}")
# >> The magic number was 42
```
## The Wove API
Here are all three of Wove's tools:
-   `weave()`: An `async` context manager that creates the execution environment for your tasks. It is used in an
    `async with` block. When the weave block ends, all tasks will be executed in the order of their dependency graph.
    The weave object has a `result` attribute that contains the results of all tasks and a `.final` attribute that
    contains the result of the last task. It can take an optional `debug` argument to print a detailed report to the
    console before executing the tasks, and an optional `max_threads` argument to set the maximum number of threads
    that Wove will use to run tasks in parallel.
-   `@w.do`: A decorator that registers a function as a task to be run within the `weave` block. It can optionally be
    passed an iterable, and if so, the task will be run concurrently for each item in the iterable. It can also be passed
    a string of another task's name, and if so, the task will be run concurrently for each item in the iterable result of
    the named task. Functions decorated with `@w.do` can be sync or async. Sync functions will be run in a background
    thread pool to avoid blocking the event loop.
-   `merge()`: A function that can be called from within a weave block to run a function concurrently for each item in
    an iterable. It should be awaited, and will return a list of results of each concurrent function call. The function
    passed in can be any function inside or outside the weave block, async or sync. Sync functions will be run in a
    background thread pool to avoid blocking the event loop.
## More Spice
This example demonstrates a more complex ML workflow using Wove's advanced features, including inheritable Weaves and enhanced task parameters.

```python
# Save as ml_pipeline.py and run `python ml_pipeline.py`
import time
import numpy as np
from wove import Weave, weave

# Define the workflow as a reusable class inheriting from `wove.Weave`.
class MLPipeline(Weave):
    def __init__(self, num_records: int):
        self.num_records = num_records
        super().__init__()

    # Use the class-based decorator `@Weave.do`.
    # Add robustness: retry on failure and timeout if it takes too long.
    @Weave.do(retries=2, timeout=60.0)
    def load_raw_data(self):
        print(f"-> [1] Loading raw data ({self.num_records} records)...")
        time.sleep(0.05)  # Simulate I/O
        features = np.arange(self.num_records, dtype=np.float64)
        print("<- [1] Raw data loaded.")
        return features

    # This mapped task processes data in chunks.
    # `workers=4` limits concurrency to 4 chunks at a time.
    # `limit_per_minute=600` throttles new tasks to 10/sec.
    @Weave.do("load_raw_data", workers=4, limit_per_minute=600)
    def process_batches(self, chunk):
        processed_chunk = np.vstack([chunk, chunk**2]).T
        print(f"    -> Processed batch of size {len(chunk)}")
        return processed_chunk

    # This final task waits for all batches to be processed.
    @Weave.do
    def train_model(self, process_batches):
        print("-> [3] Training model...")
        design_matrix = np.vstack(process_batches)
        print(f"<- [3] Model trained. Shape: {design_matrix.shape}")
        return {"status": "trained", "shape": design_matrix.shape}

# --- Synchronous Execution ---
# Pass the class to the context manager to instantiate and run it.
with weave(MLPipeline(num_records=100_000)) as w:
    # The pipeline runs here. You could override tasks inside this
    # block if needed.
    pass

print(f"\nFinal model status: {w.result.final}")
# >> Final model status: {'status': 'trained', 'shape': (100000, 2)}
```
## Advanced Features
### Enhanced `@w.do` Parameters
The `@w.do` decorator is enhanced with optional parameters for greater control:
-   **`retries: int`**: The number of times to re-run a task if it raises an exception.
-   **`timeout: float`**: The maximum number of seconds a task can run before being cancelled.
-   **`workers: int`**: For mapped tasks, this limits the number of **concurrent** executions to the specified integer.
-   **`limit_per_minute: int`**: For mapped tasks, this throttles their execution to a maximum number per minute.

### Inheritable Weaves
This feature introduces a class-based method for defining reusable workflows that can be customized inline.

**1. Defining a Parent Weave**

Workflows are defined as classes inheriting from `wove.Weave`. Tasks are defined as methods using the **`@Weave.do`** decorator.

```python
# In reports.py
from wove import Weave

class StandardReport(Weave):
    """A reusable Weave template."""
    @Weave.do(retries=2, timeout=5.0)
    def fetch_data(self, user_id: int):
        # ... logic to fetch from a database or API ...
        print(f"Fetching data for user {user_id}...")
        return {"id": user_id, "name": "Standard User"}

    @Weave.do
    def generate_summary(self, fetch_data: dict):
        return f"Report for {fetch_data['name']}"
```

**2. Inline Customization**

Pass the `Weave` class to the `weave` context manager. Inside the `with` block, use the instance's `@w.do` decorator to override parent tasks or add new ones. Overridden tasks automatically inherit parameters (`retries`, `timeout`, etc.) from the parent, which you can modify.

```python
# In views.py
from wove import weave
# from .reports import StandardReport # Assuming StandardReport is in reports.py

# This can be a standard synchronous function
def admin_report_view(user_id: int):
    # Use the synchronous `weave` block for convenience
    with weave(StandardReport(user_id=user_id)) as w:
        # This override inherits `retries=2` from the parent,
        # but changes `timeout` from 5.0 to 10.0.
        @w.do(timeout=10.0)
        def fetch_data(user_id: int):
            print(f"Fetching data for ADMIN {user_id}...")
            return {"id": user_id, "name": "Admin"}

    # The result of the final task in the graph
    return w.result.generate_summary

# print(admin_report_view(user_id=123))
# >> Fetching data for ADMIN 123...
# >> Report for Admin
```

### Dynamic Task Mapping
You can also map a task over the result of another task by passing the upstream task's name as a string to the decorator. This is useful when the iterable is generated dynamically. Wove ensures the upstream task completes before starting the mapped tasks.
```python
import asyncio
from wove import weave
async def main():
    async with weave() as w:
        # This task generates the data we want to map over.
        @w.do
        async def numbers():
            return [10, 20, 30]
        # This task is mapped over the *result* of `numbers`.
        # The `item` parameter receives each value from the list [10, 20, 30].
        @w.do("numbers")
        async def squares(item):
            return item * item
        # This final task collects the results.
        @w.do
        def summarize(squares):
            return f"Sum of squares: {sum(squares)}"
    print(w.result.final)
asyncio.run(main())
# Expected output:
# Sum of squares: 1400
```
### Complex Task Graphs
Wove can handle complex task graphs with nested `weave` blocks, `@w.do` decorators, and `merge` functions. Before a 
`weave` block is executed, wove builds a dependency graph from the function signatures and creates a plan to execute
the tasks in the correct order such that tasks run as concurrently and as soon as possible.
In addition to typical map-reduce patterns, you can also implement diamond graphs and other complex task graphs. A 
"diamond" dependency graph is one where multiple concurrent tasks depend on a single upstream task, and a final
downstream task depends on all of them.
```python
import asyncio
from wove import weave
async def main():
    async with weave() as w:
        @w.do
        async def fetch_user_id():
            return 123
        @w.do
        async def fetch_user_profile(fetch_user_id):
            print(f"-> Fetching profile for user {fetch_user_id}...")
            await asyncio.sleep(0.1)
            return {"name": "Alice"}
        @w.do
        async def fetch_user_orders(fetch_user_id):
            print(f"-> Fetching orders for user {fetch_user_id}...")
            await asyncio.sleep(0.1)
            return [{"order_id": 1, "total": 100}, {"order_id": 2, "total": 50}]
        @w.do
        def generate_report(fetch_user_profile, fetch_user_orders):
            name = fetch_user_profile["name"]
            total_spent = sum(order["total"] for order in fetch_user_orders)
            return f"Report for {name}: Total spent: ${total_spent}"
    print(w.result.final)
asyncio.run(main())
# Expected output (the first two lines may be swapped):
# -> Fetching profile for user 123...
# -> Fetching orders for user 123...
# Report for Alice: Total spent: $150
```
### Error Handling
If any task raises an exception, Wove halts execution, cancels all other running tasks, and re-raises the original 
exception from the `async with weave()` block. This ensures predictable state and allows you to use standard 
`try...except` blocks.
### Debugging & Introspection
Need to see what's going on under the hood?
-   `async with weave(debug=True) as w:`: Prints a detailed, color-coded execution plan to the console before running.
-   `w.execution_plan`: After the block, this dictionary contains the full dependency graph and execution tiers.
-   `w.result.timings`: A dictionary mapping each task name to its execution duration in seconds.

### Data-Shaping Helper Functions
`wove` provides a set of simple, composable helper functions for common data manipulation patterns. Import them from `wove.helpers`.
-   **`flatten(list_of_lists)`**: Converts a 2D iterable into a 1D list.
-   **`fold(a_list, size)`**: Converts a 1D list into a list of smaller lists.
-   **`undict(a_dict)`**: Converts a dictionary into a list of `[key, value]` pairs.
-   **`redict(list_of_pairs)`**: Converts a list of key-value pairs back into a dictionary.
-   **`denone(an_iterable)`**: Removes all `None` values from an iterable.

## More Examples
See the runnable scripts in the `examples/` directory for additional advanced examples.
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
The core of Wove's functionality is the `weave` context manager. It is used in an inline `with` block to define a list of tasks that will be executed as concurrently and as soon as possible. When Python closes the weave block, the tasks are executed immediately based on a dependency graph that Wove builds from the function signatures.

```python
import time
from wove import weave

with weave() as w:
    # These first two tasks run concurrently.
    @w.do
    def magic_number():
        time.sleep(1.0)
        return 42
    @w.do
    def important_text():
        time.sleep(1.0)
        return "The meaning of life"
    # This task depends on the first two. It runs only after both are complete.
    @w.do
    def put_together(important_text, magic_number):
        return f"{important_text} is {magic_number}!"

print(w.result.final)
# >> The meaning of life is 42!

# Access other task results by name.
print(f"The magic number was {w.result.magic_number}")
# >> The magic number was 42
```
## Core API
The two main Wove tools are:
-   `weave()`: An `async` context manager used in either a `with` or `async with` block that creates the execution environment for your tasks. When the weave block ends, all tasks will be executed in the order of their dependency graph. The weave object has a `result` attribute that contains the results of all tasks and a `.final` attribute that contains the result of the last task. It can take an optional `debug` argument to print a detailed report to the console before executing the tasks, and an optional `max_threads` argument to set the maximum number of threads that Wove will use to run tasks in parallel.
-   `@w.do`: A decorator that registers a function as a task to be run within the `weave` block. It can be used on both `def` and `async def` functions, with non-async functions being run in a background thread pool to avoid blocking the event loop. It can optionally be passed an iterable, and if so, the task will be run concurrently for each item in the iterable. It can also be passed a string of another task's name, and if so, the task will be run concurrently for each item in the iterable result of the named task. It accepts several other optional parameters for greater control over task execution, including `retries`, `timeout`, `workers`, and `limit_per_minute`.

## More Spice
This example demonstrates using Wove's advanced features, including inheritable overridable Weaves, static task mapping, dynamic task mapping, merging external functions, and a complex task graph.
```python
import time
import numpy as np
from wove import Weave, weave

class DiamondPipeline(Weave):
    def __init__(self, num_records: int):
        self.num_records = num_records
        super().__init__()
    @Weave.do(retries=2, timeout=60.0)
    def load_data(self):
        # Initial data loading - the top of the diamond.
        time.sleep(0.1)
        data = np.linspace(0, 10, self.num_records)
        return data
    @Weave.do("load_data")
    def feature_a(self, item):
        # First parallel processing branch.
        time.sleep(0.2)
        result = np.sin(item)
        return result
    @Weave.do("load_data")
    def feature_b(self, item):
        # Second parallel processing branch.
        time.sleep(0.3)
        result = np.cos(item)
        return result
    @Weave.do
    def merged_features(self, feature_a, feature_b):
        # Merge the results from parallel branches - bottom of the diamond.
        merged = np.column_stack(feature_a + feature_b)
        return merged
    @Weave.do
    def report(self, merged_features):
        """Create a report from the merged features."""
        return {
            "mean": float(np.mean(merged_features)),
            "std": float(np.std(merged_features)),
            "shape": merged_features.shape
        }

# Run the pipeline
with weave(DiamondPipeline(num_records=1_000)) as w:
    # You can customize any step. `do` params are inherited.
    @w.do
    def feature_a(item):
        result = np.tanh(item)
        return result

print(f"\nPipeline complete. Results: {w.result.final}")
# >> Pipeline complete. Results: {'mean': 0.0, 'std': 1.0, 'shape': (1000, 2)}
```
## Advanced Features
### Task parameters
The `@w.do` decorator has several optional parameters for convenience:
-   **`retries: int`**: The number of times to re-run a task if it raises an exception.
-   **`timeout: float`**: The maximum number of seconds a task can run before being cancelled.
-   **`workers: int`**: For mapped tasks, this limits the number of **concurrent** executions to the specified integer.
-   **`limit_per_minute: int`**: For mapped tasks, this throttles their execution to a maximum number per minute.

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
Wove can handle complex task graphs with nested `weave` blocks, `@w.do` decorators, and `merge` functions. Before a `weave` block is executed, wove builds a dependency graph from the function signatures and creates a plan to execute the tasks in the correct order such that tasks run as concurrently and as soon as possible. In addition to typical map-reduce patterns, you can also implement diamond graphs and other complex task graphs. A "diamond" dependency graph is one where multiple concurrent tasks depend on a single upstream task, and a final downstream task depends on all of them.
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

If you pass a `Weave` subclass to the `weave` context manager, you can customize it inline. Inside the `with` block, use the instance's `@w.do` decorator to override parent tasks or add new ones. Overridden tasks automatically inherit parameters (`retries`, `timeout`, etc.) from the parent as defaults.

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
### Error Handling
If any task raises an exception, Wove halts execution, cancels all other running tasks, and re-raises the original exception from the `async with weave()` block. This ensures predictable state and allows you to use standard `try...except` blocks.
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
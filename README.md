# Wove
Beautiful Python async.
## What is Wove For?
Wove is for running high latency async tasks like web requests and database queries concurrently in the same way as 
asyncio, but with a drastically improved user experience.
Improvements compared to asyncio include:
-   **Looks Like Normal Python**: Parallelism and execution order are implicit. You write simple, decorated functions. No manual task objects, no callbacks.
-   **Reads Top-to-Bottom**: The code in a `weave` block is declared in the order it is executed inline in your code instead of in disjointed functions.
-   **Sync & Async Transparency**: Mix `async def` and `def` freely. A `weave` block be inside or outside an async context. Sync functions are run in a background thread pool to avoid blocking the event loop.
-   **Automatic Parallelism**: Wove builds a dependency graph from your function signatures and runs independent tasks concurrently as soon as possible.
-   **High Visibility**: Wove includes debugging tools that allow you to identify where exceptions and deadlocks occur across parallel tasks, and inspect inputs and outputs at each stage of execution.
-   **Normal Python Data**: Wove's task data looks like normal Python variables because it is. This is because of inherent multithreaded data safety produced in the same way as map-reduce.
-   **Minimal Boilerplate**: Get started with just the `async with weave() as w:` context manager and the `@w.do` decorator.
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
    # This block is magically like an `async with` block.
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
    # When the `with` block closes, all tasks are executed.
print(w.result.final)
# >> The meaning of life is 42!
print(f"The magic number was {w.result.magic_number}")
# >> The magic number was 42
print(f'The important text was "{w.result["important_text"]}"')
# >> The important text was "The meaning of life"
```
## Core API
The two core Wove tools are:
-   `weave()`: An `async` context manager used in either a `with` or `async with` block that creates the execution environment for your tasks. When the `weave` block ends, all tasks will be executed in the order of their dependency graph. The `weave` object has a `result` attribute that contains the results of all tasks and a `.final` attribute that contains the result of the last task.
-   `@w.do`: A decorator that registers a function as a task to be run within the `weave` block. It can be used on both `def` and `async def` functions interchangeably, with non-async functions being run in a background thread pool to avoid blocking the event loop. It can optionally be passed an iterable, and if so, the task will be run concurrently for each item in the iterable. It can also be passed a string of another task's name, and if so, the task will be run concurrently for each item in the iterable result of the named task.
## More Spice
This example demonstrates Wove's advanced features, including inheritable overridable Weaves, static task mapping, dynamic task mapping, merging an external function, and a complex task graph.
```python
import time
import numpy as np
from wove import Weave, weave, merge

# An external function that will be mapped with `merge`
def quality_check(data):
    return any(np.isnan(data))

class DataPipeline(Weave):
    def __init__(self, records: int):
        self.records = records
        super().__init__()
    @Weave.do(retries=2, timeout=60.0)
    def load_data(self):
        # Initial data loading - the top of the diamond.
        time.sleep(0.1)
        return np.linspace(0, 10, self.records)
    @Weave.do("load_data")
    def feature_a(self, item):
        # First parallel processing branch.
        time.sleep(0.2)
        return np.sin(item)
    @Weave.do("load_data")
    def feature_b(self, item):
        # Second parallel processing branch.
        time.sleep(0.3)
        return np.cos(item)
    @Weave.do
    def merged_features(self, feature_a, feature_b):
        # Merge the results from parallel branches - bottom of the diamond.
        return np.column_stack((feature_a, feature_b))
    @Weave.do
    async def report(self, merged_features):
        # Dynamically map an external function using `merge`.
        quality_result = any(await merge(quality_check, merged_features))
        quality_status = "WARN: NaN values detected" if quality_result else "OK"
        # Create a report from the merged features.
        return {
            "mean": float(np.mean(merged_features)),
            "std": float(np.std(merged_features)),
            "shape": merged_features.shape,
            "quality_status": quality_status,
        }

# Run a customized version of the pipeline
with weave(DataPipeline(records=1_000)) as w:
    # Override one of the feature steps. Any parameters in the parent are now defaults.
    @w.do("load_data")
    def feature_a(item):
        return np.tanh(item)

print(f"\nPipeline complete. Results: {w.result.final}")
# >> Pipeline complete. Results: {'mean': 0.9302537626956293, 'std': 0.18500793874408072, 'shape': (1000, 2), 'quality_status': 'OK'}
```
## Advanced Features
### Task parameters
The `@w.do` decorator has several optional parameters for convenience:
-   **`retries: int`**: The number of times to re-run a task if it raises an exception.
-   **`timeout: float`**: The maximum number of seconds a task can run before being cancelled.
-   **`workers: int`**: For mapped tasks only, this limits the number of concurrent instances of the task running at a time.
-   **`limit_per_minute: int`**: For mapped tasks only, this throttles their task instances to a maximum number per minute.
### Dynamic Task Mapping
You can also map a task over the result of another task by passing the upstream task's name as a string to the decorator. This is useful when the iterable is generated dynamically. Wove ensures the upstream task completes before starting the mapped tasks.
```python
import asyncio
from wove import weave
async def main():
    async with weave() as w:
        # Generates the data we want to map over.
        @w.do
        async def numbers():
            return [10, 20, 30]
        # Map each item produced by `numbers` to the `squares` function.
        # Each item's instance of `squares` will run concurrently, and then
        # be collected as a list after all have completed.
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
        async def user_id():
            return 123
        @w.do
        async def user_profile(user_id):
            print(f"-> Fetching profile for user {user_id}...")
            await asyncio.sleep(0.1)
            return {"name": "Alice"}
        @w.do
        async def user_orders(user_id):
            print(f"-> Fetching orders for user {user_id}...")
            await asyncio.sleep(0.1)
            return [{"order_id": 1, "total": 100}, {"order_id": 2, "total": 50}]
        @w.do
        def report(user_profile, user_orders):
            name = user_profile["name"]
            total_spent = sum(order["total"] for order in user_orders)
            return f"Report for {name}: Total spent: ${total_spent}"
    print(w.result.final)
asyncio.run(main())
# Expected output (the first two lines may be swapped):
# -> Fetching profile for user 123...
# -> Fetching orders for user 123...
# Report for Alice: Total spent: $150
```
### Inheritable Weaves
You can define reusable, overridable workflows by inheriting from `wove.Weave`.
```python
# In reports.py
from wove import Weave
class StandardReport(Weave):
    @Weave.do(retries=2, timeout=5.0)
    def fetch_data(self, user_id: int):
        # ... logic to fetch from a database or API ...
        print(f"Fetching data for user {user_id}...")
        return {"id": user_id, "name": "Standard User"}
    @Weave.do
    def generate_summary(self, fetch_data: dict):
        return f"Report for {fetch_data['name']}"
```
To call the reusable `Weave`, pass it to a `weave` context manager.
```python
from wove import weave
from .reports import StandardReport

with weave(StandardReport(user_id=123)) as w:
    pass

print(w.result.final)
```
You can override any tasks inline in your `with` block. The overrided task inherits the parent's `do` parameters if not specified.
```python
# In views.py
from wove import weave
from .reports import StandardReport

user_id = 100
with weave(StandardReport(user_id=user_id)) as w:
    @w.do(timeout=10.0) # retries=2 from parent
    def fetch_data(user_id: int):
        print(f"Fetching data for ADMIN {user_id}...")
        return {"id": user_id, "name": "Admin"}

print(w.result.generate_summary)
# print(admin_report_view(user_id=123))
# >> Fetching data for ADMIN 123...
# >> Report for Admin
```
### Merging External Functions
Wove provides the `merge` function to dynamically map any callable over an iterable. The callable (typically a function) can be defined inside or outside the weave block, and can be `async` or not. Each copy of the function will be run concurrently for each item in the iterable. Used with `await`, it will return a list of results when all instances have completed.
```python
from wove import weave, merge, flatten

def split(string):
    return string.split(" ")

with weave() as w:
    @w.do
    def strings():
        return ["hello world", "foo bar", "baz qux"]
    @w.do
    async def chop(strings):
        # Async functions can be within non-async weave blocks.
        # `merge` needs an async function so it can be awaited.
        return flatten(await merge(split, strings))

print(w.result.final)
# >> ['hello', 'world', 'foo', 'bar', 'baz', 'qux']
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
-   **`fold(a_list, size)`**: Converts a 1D list into N smaller lists of `size` length.
-   **`batch(a_list, count)`**: Converts a 1D list into `count` smaller lists of N length.
-   **`undict(a_dict)`**: Converts a dictionary into a list of `[key, value]` pairs.
-   **`redict(list_of_pairs)`**: Converts a list of key-value pairs back into a dictionary.
-   **`denone(an_iterable)`**: Removes all `None` values from an iterable.
## More Examples
See the runnable scripts in the `examples/` directory for additional advanced examples.
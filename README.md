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
Wove defines only three tools to manage all of your async needs. The core
of Wove's functionality is the `weave` context manager. It is used with an `async with` block to define a list of
tasks that will be executed as concurrently and as soon as possible. When Python closes the `weave` block, the tasks
are executed immediately based on a dependency graph that Wove builds from the function signatures.
```python
import asyncio
from wove import weave
async def main():
    async with weave() as w:
        @w.do
        async def magic_number():
            await asyncio.sleep(1.0)
            return 42
        @w.do
        async def important_text():
            await asyncio.sleep(1.0)
            return "The meaning of life"
        @w.do
        async def put_together(important_text, magic_number):
            return f"{important_text} is {magic_number}!"
    print(w.result.final)
asyncio.run(main())
>> The meaning of life is 42!
```
In the example above, `magic_number` and `important_text` are called concurrently. The magic doesn't stop there.
## The Wove API
Here are all three of Wove's tools:
-   `weave()`: An `async` context manager that creates the execution environment for your tasks. It is used in an 
    `async with` block. When the weave block ends, all tasks will be executed in the order of their dependency graph.
    The weave object has a `result` attribute that contains the results of all tasks and a `.final` attribute that
    contains the result of the last task.
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
Here is a more complex example that showcases Wove's core features working together: static and dynamic task mapping, the `merge` function for dynamic calls, and a diamond-shaped dependency graph.
```python
import asyncio
import time
from wove import weave, merge

# A function to be called dynamically with `merge`.
# Wove runs this sync function in a thread pool.
def analyze_item(item: int):
    """A simple synchronous, CPU-bound-style function."""
    print(f"    -> Analyzing item {item}...")
    time.sleep(0.05) # Simulate work
    return {"item": item, "is_even": item % 2 == 0}

async def main():
    """Demonstrates Wove's core features in a single example."""
    async with weave() as w:
        # 1. STATIC MAPPING: Maps `process_extra` over a predefined list.
        #    This task runs concurrently with `source_data`.
        @w.do([100, 200])
        def process_extra(item):
            print(f"-> Processing extra item {item}...")
            return item / 10

        # 2. SOURCE TASK: The top of our "diamond" dependency graph.
        @w.do
        async def source_data():
            print("-> Fetching source data...")
            await asyncio.sleep(0.01)
            return [1, 2, 3]

        # 3. DYNAMIC MAPPING (Side A): Maps over the result of `source_data`.
        @w.do("source_data")
        def squares(item):
            print(f"  -> Squaring {item}...")
            return item * item

        # 4. DYNAMIC MAPPING (Side B): Also maps over `source_data` and runs
        #    concurrently with the `squares` task.
        @w.do("source_data")
        def cubes(item):
            print(f"  -> Cubing {item}...")
            return item * item * item

        # 5. MERGE: Depends on `squares` results and uses `merge` to run
        #    a dynamic, concurrent analysis on them.
        @w.do
        async def analysis(squares):
            print(f"-> Analyzing squared numbers: {squares}")
            # `merge` calls `analyze_item` for each number in parallel.
            results = await merge(analyze_item, squares)
            return results

        # 6. FINAL TASK (Bottom of Diamond): Depends on multiple upstream tasks,
        #    collecting all results into a final report.
        @w.do
        def final_report(process_extra, cubes, analysis):
            print("-> Generating final report...")
            return {
                "extra_results": process_extra,
                "cubed_results": cubes,
                "analysis": analysis,
            }

    # Results are available after the block exits.
    print(f"\nFinal Report: {w.result.final}")

asyncio.run(main())
# Expected output (order of concurrent tasks may vary):
# -> Processing extra item 100...
# -> Fetching source data...
# -> Processing extra item 200...
#   -> Squaring 1...
#   -> Cubing 1...
#   -> Squaring 2...
#   -> Cubing 2...
#   -> Squaring 3...
#   -> Cubing 3...
# -> Analyzing squared numbers: [1, 4, 9]
#     -> Analyzing item 1...
#     -> Analyzing item 4...
#     -> Analyzing item 9...
# -> Generating final report...
#
# Final Report: {'extra_results': [10.0, 20.0], 'cubed_results': [1, 8, 27], 'analysis': [{'item': 1, 'is_even': False}, {'item': 4, 'is_even': True}, {'item': 9, 'is_even': False}]}
```
## Advanced Features
### Task Mapping
In the style of map-reduce, iterables can be mapped to tasks with `@w.do(iterable)` and `merge(function, iterable)`. 
The mapped function will be executed concurrently for each item in the iterable. All task results are consolidated in
the results object which can be accessed like a collection.
```python
ids = [1, 2, 3]
async with weave() as w:
    # For each id, fetch its username. All "username" tasks will run concurrently.
    @w.do(ids)
    async def username(user_id):
        return f"User {user_id}"
    
    # Collect the usernames into a map.
    @w.do
    async def collect(username):
        return {i: u for i, u in enumerate(username)}
print(w.result.final)
>> {0: 'User 1', 1: 'User 2', 2: 'User 3'}
print(w.result['username'])
>> ['User 1', 'User 2', 'User 3']
print(w.result['collect'])
>> {0: 'User 1', 1: 'User 2', 2: 'User 3'}
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
## More Examples
See the runnable scripts in the `examples/` directory for additional advanced examples.
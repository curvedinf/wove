# Wove
Beautiful Python async.

## Core Concepts
Wove is made from sensical philosophies that make async code feel more Pythonic.

-   **Looks Like Normal Python**: You write simple, decorated functions. No manual task objects, no callbacks.
-   **Reads Top-to-Bottom**: The code in a `weave` block is declared in a logical order, but `wove` intelligently determines the optimal *execution* order.
-   **Automatic Parallelism**: Wove builds a dependency graph from your function signatures and runs independent tasks concurrently.
-   **Normal Python Data**: Wove's task data looks like normal Python variables because it is, creating inherent multithreaded data safety in the same way as map-reduce.
-   **Minimal Boilerplate**: Get started with just the `async with weave() as w:` context manager and the `@w.do` decorator.
-   **Sync & Async Transparency**: Mix `async def` and `def` functions freely. `wove` automatically runs synchronous functions in a background thread pool to avoid blocking the event loop.
-   **Zero Dependencies**: Wove is pure Python, using only the standard library and can be integrated into any Python project.

## Installation
Download wove with pip:
```bash
pip install wove
```

## The Basics
Wove defines only three tools to manage all of your async needs, but you can do a lot with just two of them:

```python
import asyncio
from wove import weave

async def main():
    async with weave() as w:
        @w.do
        async def magic_number():
            return 42
        @w.do
        async def important_text():
            return "The meaning of life"
        @w.do
        async def put_together(important_text, magic_number):
            return f"{important_text} is {magic_number}!"
    print(w.result.final)
asyncio.run(main())

>> The meaning of life is 42!
```

In the example above, `magic_number` and `important_text` are called in parallel. The magic doesn't stop there.

## The Wove API

Here are all three of Wove's tools:

-   `weave()`: An `async` context manager that creates the execution environment for your tasks.
-   `@w.do`: A decorator that registers a function as a task to be run within the `weave` block.
-   `merge()`: A function to dynamically call and `await` other functions from *inside* a running task.


## More Spice

Here is a more complex example that uses extra-powerful Wove features:

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
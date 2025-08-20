# Wove
Beautiful python async orchestration.
Wove provides a simple context manager (`weave`) and decorator (`@w.do`) to run async and sync functions concurrently, automatically managing dependencies between them. It's particularly useful for I/O-bound tasks, like making database queries or calling external APIs in a web request.
## Installation
This project is not yet on PyPI. To install locally for development:
```bash
pip install -e .
```
## Usage
Here's an example of how to use Wove in a Django-style async view to fetch data from the database concurrently. `wove` automatically discovers the dependencies between your functions (`author` and `comments` both depend on `post`) and executes them with maximum concurrency.
The full code for this example can be found in `examples/example.py`.
```python
# A simplified example (full version in examples/example.py)
from django.http import JsonResponse
import wove
from wove import weave
# Assume these are async functions that fetch data from a DB/API
async def fetch_post(post_id: int): ...
async def fetch_author(author_id: int): ...
async def fetch_comments(post_id: int): ...
async def post_detail_view(request, post_id: int):
    """
    Fetches post details, author, and comments concurrently.
    """
    async with weave() as w:
        @w.do
        async def post():
            return await fetch_post(post_id)
        
        @w.do
        async def author(post):
            # Depends on `post`
            if not post: return None
            return await fetch_author(post['author_id'])
            
        @w.do
        async def comments(post):
            # Depends on `post`, runs in parallel with `author`
            if not post: return []
            return await fetch_comments(post['id'])
            
        @w.do
        def composed_response(post, author, comments):
            if not post:
                return {"error": "Post not found"}
            post['author'] = author
            post['comments'] = comments
            return post
            
    # .final is a shortcut to the result of the last task
    return JsonResponse(w.result.final)
```
## How it Works
`wove` orchestrates your functions by building and executing a dependency graph.
1.  **`async with weave() as w:`**: This context manager creates an execution environment. All functions decorated with `@w.do` inside this block are registered as tasks to be run. The `w` object holds the decorator and the final results.
2.  **`@w.do` and Dependency Injection**: The `@w.do` decorator marks a function as a task. `wove` inspects the function's signature to determine its dependencies. If a task `b` has a parameter named `a`, `wove` assumes `b` depends on the result of task `a`. It will wait for `a` to finish and then "inject" its result as an argument when calling `b`.
3.  **Graph Building and Execution**: Internally, `wove` builds a Directed Acyclic Graph (DAG) of your tasks. It then performs a topological sort to determine the execution order. Tasks with no unmet dependencies are run concurrently. As tasks complete, their dependents are scheduled to run, ensuring maximum parallelism while respecting the dependency structure. If a circular dependency is detected, a `RuntimeError` is raised.
4.  **Sync and Async Transparency**: `wove` handles both `async` and regular synchronous functions automatically. Async functions run on the event loop, while sync functions are executed in a background thread pool (`asyncio.run_in_executor`) to avoid blocking.
5.  **Results**: Once the `async with` block exits, all tasks have completed. You can access results via the `w.result` object by name (`w.result['post']`), unpack them in definition order (`p, a, c, r = w.result`), or use the `.final` property as a shortcut for the last-defined task's result (`w.result.final`).
## Advanced Usage
### Error Handling
When a task raises an exception, `wove` ensures predictable and safe cleanup:
*   **Execution Halts**: No new tasks are scheduled to run.
*   **Cancellation**: All other tasks that are currently running are immediately cancelled via `asyncio.Task.cancel()`.
*   **Propagation**: The original exception is re-raised from the `async with weave()` block, allowing you to catch it with a standard `try...except` block.
A full, runnable example demonstrating this behavior can be found in `examples/error_handling.py`.
### Task Mapping for Parallelism
`wove` can automatically run a task concurrently for each item in an iterable. This is a powerful feature for batch processing, such as making multiple API calls or running database queries in parallel.
To use mapping, pass an iterable (like a list or range) to the `@w.do` decorator: `@w.do(items_to_process)`.
A runnable example demonstrating this feature can be found in `examples/api_aggregator.py`. Here is a simplified snippet:
```python
import asyncio
from wove import weave
async def run_mapping_example():
    user_ids = [1, 2, 3]
    
    async def fetch_user_profile(user_id):
        await asyncio.sleep(0.1)
        return {"id": user_id, "name": f"User {user_id}"}
    async with weave() as w:
        # This task will run 3 times, once for each ID.
        @w.do(user_ids)
        async def user_profile(user_id):
            return await fetch_user_profile(user_id)
        @w.do
        def summarize_results(user_profile):
            # `user_profile` is now a list of results.
            names = [p['name'] for p in user_profile]
            return f"Processed users: {', '.join(names)}"
    print(f"Summary: {w.result.final}")
```
**Key Points:**
*   **Signature**: The mapped function must have exactly one parameter that is not a dependency on another task. `wove` uses this parameter to pass in items from the iterable.
*   **Dependencies**: The results of dependency tasks are passed to *every* concurrent execution of the mapped function.
*   **Results**: The result of the mapped task is a list containing the return value from each individual execution, in the same order as the input iterable.
*   **Downstream Tasks**: A task that depends on a mapped task will receive the entire list of results.
### Dynamic Task Execution with `merge`
While `@w.do` is excellent for defining a static dependency graph, sometimes you need to dynamically execute functions from within a running task. `wove` provides the `merge` function for this purpose.
`merge` allows you to call any async or sync function from inside a task and have its result integrated back into the `asyncio` event loop managed by `wove`. It's particularly useful for conditional logic or complex workflows where the exact functions to be called are not known until runtime.
A full, runnable example can be found in `examples/dynamic_workflow.py`. It shows how to dynamically choose which function to run based on a user's role.
**Key Features:**
*   **Dynamic Execution**: Call functions on the fly from within any `@w.do` task.
*   **Sync/Async Transparency**: Just like `@w.do`, `merge` handles both `async` and regular synchronous functions.
*   **Iterable Mapping**: `merge` can execute a function concurrently for each item in an iterable.
*   **Recursion Guard**: `merge` raises a `RecursionError` if the call depth exceeds 100.
**Important Note**: Unlike `@w.do`, `merge` does **not** perform automatic dependency injection. You must pass all required arguments, often using `functools.partial` or a `lambda`.
### Debugging and Introspection
`wove` provides a powerful debugging mode and programmatic access to its execution plan, allowing you to inspect the dependency graph and performance of your tasks.
To enable the debug mode, simply pass `debug=True` to the `weave` context manager. This will print a detailed report to your console before the tasks are executed.
```python
import asyncio
from wove import weave

async def main():
    async with weave(debug=True) as w:
        @w.do
        async def task_a():
            return "A"
        @w.do
        def task_b(task_a):
            return "B"

if __name__ == "__main__":
    asyncio.run(main())
```
The debug report provides a clear, color-coded overview of the detected tasks, their connections, and the exact execution plan. This is invaluable for understanding how `wove` will orchestrate your functions.
Here is an example of the output:
```text
--- Wove Debug Report ---

Detected Tasks (2):
  • task_a
  • task_b

Dependency Graph:
  • task_a
    - Dependencies: None
    - Dependents:   task_b
  • task_b
    - Dependencies: task_a
    - Dependents:   None

Execution Plan:
  Tier 1
    - task_a (async)
  Tier 2
    - task_b (sync)

--- Starting Execution ---
```
For more advanced use cases, you can access the execution plan and task timings directly from the context manager instance after the `async with` block completes.
*   **`w.execution_plan`**: A dictionary containing the complete dependency graph (`dependencies`, `dependents`), the execution `tiers`, and the topologically `sorted_tasks`.
    ```python
    async with weave() as w:
        @w.do
        def task_a(): pass
        @w.do
        def task_b(task_a): pass

    plan = w.execution_plan
    print(plan["tiers"])  # Output: [['task_a'], ['task_b']]
    ```
*   **`w.result.timings`**: A dictionary mapping each task's name to its execution duration in seconds. This is extremely useful for identifying performance bottlenecks.
    ```python
    import asyncio
    from wove import weave
    
    async def main():
        async with weave() as w:
            @w.do
            async def slow_task():
                await asyncio.sleep(0.1)

        print(f"slow_task took: {w.result.timings['slow_task']:.2f}s")
        # Output: slow_task took: 0.10s
        
    asyncio.run(main())
    ```
### Complex Dependency Chains
`wove` can handle arbitrarily complex dependency graphs, not just simple linear or one-to-many patterns. The following example demonstrates a "diamond" dependency, where two tasks run concurrently and their results are combined by a final task.
```python
import asyncio
from wove import weave
async def run_diamond_example():
    async with weave() as w:
        @w.do
        def initial_data():
            return {"value": "data"}
        @w.do
        async def process_a(initial_data):
            await asyncio.sleep(0.1)
            return f"Processed A on {initial_data['value']}"
        @w.do
        async def process_b(initial_data):
            await asyncio.sleep(0.2)
            return f"Processed B on {initial_data['value']}"
        @w.do
        def combine(process_a, process_b):
            return {"a_result": process_a, "b_result": process_b}
    print(f"Final result: {w.result.final}")
```
## More Examples
The `examples/` directory contains more detailed scripts demonstrating common patterns:
*   **`api_aggregator.py`**: Uses task mapping (`@w.do(iterable)`) to concurrently fetch details for a list of items from a real-world public API. This pattern is ideal for batch processing.
*   **`dynamic_workflow.py`**: Shows how to use `merge` to build workflows with conditional branching, where the next function to call is decided at runtime.
*   **`error_handling.py`**: A clear demonstration of how Wove cancels running tasks and propagates exceptions when one task fails.
*   **`etl_pipeline.py`**: A more advanced `merge` example, showcasing a "fan-out, fan-in" graph where a dispatcher dynamically assigns different transformation functions to data records based on their type.
*   **`example.py`**: A complete Django-style view that fetches a primary resource and its related data concurrently, and uses `merge` for conditional logic.
*   **`file_processor.py`**: A complex pipeline showing nested parallelism. It uses task mapping (`@w.do(iterable)`) to process files concurrently, and within each file task, it uses `merge(callable, iterable)` to process words in parallel.
*   **`ml_pipeline.py`**: Demonstrates a "diamond" dependency graph for a machine learning workflow, parallelizing feature engineering tasks.

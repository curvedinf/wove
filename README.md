# Wove
Beautiful python async orchestration.
Wove provides a simple context manager (`weave`) and decorator (`@w.do`) to run async and sync functions concurrently, automatically managing dependencies between them. It's particularly useful for I/O-bound tasks, like making database queries or calling external APIs in a web request.
## Installation
This project is not yet on PyPI. To install locally for development:
```bash
pip install -e .
```
## Usage
Here's an example of how to use Wove in a Django async view to fetch data from the database concurrently. `wove` automatically discovers the dependencies between your functions (`author` and `comments` both depend on `post`) and executes them with maximum concurrency.
The full code for this example can be found in `examples/example.py`.
```python
# examples/example.py (showing a Django-style view)
from django.http import JsonResponse
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
# NOTE: Post and Comment are fictional models for demonstration.
# from .models import Post, Comment 
import wove
from wove import weave
async def post_detail_view(request, post_id: int):
    """
    Fetches post details, author, and comments concurrently.
    """
    async with weave() as w:
        @w.do
        def post():
            # In a real Django app, you would use async ORM calls
            # or wrap sync calls like this.
            post_lookup = sync_to_async(Post.objects.values().get)
            return await post_lookup(id=post_id)
        @w.do
        def author(post):
            author_lookup = sync_to_async(
                User.objects.values('username', 'email').get
            )
            return await author_lookup(id=post['author_id'])
        @w.do
        def comments(post):
            comments_lookup = sync_to_async(
                lambda: list(Comment.objects.values('author_name', 'text').filter(post_id=post['id']))
            )
            return await comments_lookup()
        # This task depends on the previous three and composes the final response.
        @w.do
        def composed_response(post, author, comments):
            post['author'] = author
            post['comments'] = comments
            return post
    # The `.final` property is a convenient shortcut to the result
    # of the last-defined task in the `weave` block.
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
```python
import asyncio
from wove import weave
async def run_error_example():
    was_cancelled = False
    print("--- Running Error Handling Example ---")
    try:
        async with weave() as w:
            @w.do
            async def long_task():
                nonlocal was_cancelled
                try:
                    await asyncio.sleep(2) # Long I/O operation
                except asyncio.CancelledError:
                    was_cancelled = True
                    print("long_task was cancelled as expected.")
                    raise
                return "should not finish"
            @w.do
            async def failing_task():
                await asyncio.sleep(0.1) # Let long_task start
                raise ValueError("Something went wrong")
            @w.do
            def dependent_task(failing_task):
                # This will never run
                return "never"
    except ValueError as e:
        print(f"Caught expected exception: {e}")
    
    assert was_cancelled, "The long-running task was not cancelled."
    print("--- Error Handling Example Finished ---")
# To run this example:
# if __name__ == "__main__":
#     asyncio.run(run_error_example())
```
### Task Mapping for Parallelism
`wove` can automatically run a task concurrently for each item in an iterable. This is a powerful feature for batch processing, such as making multiple API calls or running database queries in parallel.
To use mapping, pass an iterable (like a list or range) to the `@w.do` decorator: `@w.do(items_to_process)`.
```python
import asyncio
from wove import weave
async def run_mapping_example():
    user_ids = [1, 2, 3]
    async def fetch_user_profile(user_id):
        """Simulates fetching a user profile from an API."""
        print(f"Fetching profile for user {user_id}...")
        await asyncio.sleep(0.1)
        return {"id": user_id, "name": f"User {user_id}"}
    async with weave() as w:
        @w.do
        def site_config():
            return {"api_version": "v3"}
        # The `process_user` task will run 3 times, once for each ID.
        # It depends on `site_config`, which is passed to every call.
        # The `user_id` parameter receives the item from the iterable.
        @w.do(user_ids)
        async def process_user(user_id, site_config):
            profile = await fetch_user_profile(user_id)
            print(f"Processing profile for {profile['name']} with API {site_config['api_version']}")
            return {"processed_name": profile['name'].upper()}
        @w.do
        def summarize_results(process_user):
            # `process_user` is now a list of results.
            names = [result['processed_name'] for result in process_user]
            return f"Processed users: {', '.join(names)}"
    # The result of a mapped task is a list of the results from each run.
    assert w.result['process_user'] == [
        {'processed_name': 'USER 1'},
        {'processed_name': 'USER 2'},
        {'processed_name': 'USER 3'}
    ]
    print(f"Summary: {w.result.final}")
# To run this example:
# if __name__ == "__main__":
#     asyncio.run(run_mapping_example())
```
**Key Points:**
*   **Signature**: The mapped function must have exactly one parameter that is not a dependency on another task. `wove` uses this parameter to pass in items from the iterable. In the example above, `user_id` is the item parameter.
*   **Dependencies**: All other parameters are treated as dependencies. The results of dependency tasks (like `site_config`) are passed to *every* concurrent execution of the mapped function.
*   **Results**: The result of the mapped task (e.g., `w.result['process_user']`) is a list containing the return value from each individual execution, in the same order as the input iterable.
*   **Downstream Tasks**: A task that depends on a mapped task will receive the entire list of results.
### Complex Dependency Chains
`wove` can handle arbitrarily complex dependency graphs, not just simple linear or one-to-many patterns. The following example demonstrates a "diamond" dependency, where two tasks run concurrently and their results are combined by a final task.
```python
import asyncio
from wove import weave
async def run_diamond_example():
    print("--- Running Diamond Dependency Example ---")
    async with weave() as w:
        @w.do
        def initial_data():
            print("Fetching initial data...")
            return {"id": 123, "value": "data"}
        @w.do
        async def process_a(initial_data):
            print("Processing data path A (0.1s)...")
            await asyncio.sleep(0.1)
            return f"Processed A on {initial_data['value']}"
        @w.do
        async def process_b(initial_data):
            print("Processing data path B (0.2s)...")
            await asyncio.sleep(0.2)
            return f"Processed B on {initial_data['value']}"
        @w.do
        def combine(process_a, process_b):
            print("Combining results...")
            return {"a_result": process_a, "b_result": process_b}
    print(f"Final result: {w.result.final}")
    print("--- Diamond Dependency Example Finished ---")
# To run this example:
# if __name__ == "__main__":
#     asyncio.run(run_diamond_example())
```
## More Examples
The `examples/` directory contains more detailed scripts demonstrating common patterns:
*   **`etl_pipeline.py`**: Showcases a "fan-out, fan-in" dependency graph. A single data extraction task is followed by multiple concurrent transformation tasks, whose results are then combined by a final loading task. This is a common pattern for parallel data processing.
*   **`ml_pipeline.py`**: Demonstrates a "diamond" dependency graph for a machine learning workflow. A data loading task feeds into two parallel feature engineering tasks, which are then combined by a final model training task.
*   **`api_aggregator.py`**: Uses task mapping to concurrently fetch details for a list of items from a simulated API. This pattern is ideal for batch processing records or aggregating data from multiple endpoints.

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

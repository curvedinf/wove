# Wove

Beautiful python async orchestration.

Wove provides a simple context manager (`weave`) and decorator (`@do`) to run async and sync functions concurrently, automatically managing dependencies between them. It's particularly useful for I/O-bound tasks, like making database queries or calling external APIs in a web request.

## Installation

This project is not yet on PyPI. To install locally for development:

```bash
pip install -e .
```

## Usage

Here's an example of how to use Wove in a Django async view to fetch data from the database concurrently. `wove` automatically discovers the dependencies between your functions (`author` and `comments` both depend on `post`) and executes them with maximum concurrency.

```python
# your_app/views.py
from django.http import JsonResponse
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

# NOTE: Post and Comment are fictional models for demonstration.
# from .models import Post, Comment 

import wove
from wove import weave, do

async def post_detail_view(request, post_id: int):
    """
    Fetches post details, author, and comments concurrently.
    """
    async with weave() as result:
        @do
        def post():
            # In a real Django app, you would use async ORM calls
            # or wrap sync calls like this.
            post_lookup = sync_to_async(Post.objects.values().get)
            return await post_lookup(id=post_id)

        @do
        def author(post):
            author_lookup = sync_to_async(
                User.objects.values('username', 'email').get
            )
            return await author_lookup(id=post['author_id'])

        @do
        def comments(post):
            comments_lookup = sync_to_async(
                lambda: list(Comment.objects.values('author_name', 'text').filter(post_id=post['id']))
            )
            return await comments_lookup()

        # This task depends on the previous three and composes the final response.
        @do
        def composed_response(post, author, comments):
            post['author'] = author
            post['comments'] = comments
            return post

    # The `.final` property is a convenient shortcut to the result
    # of the last-defined task in the `weave` block.
    return JsonResponse(result.final)
```

### How it Works

1.  **`async with weave() as result:`**: Creates a context where concurrent tasks can be defined. The `result` object will hold the output of all tasks once they complete.
2.  **`@do`**: This decorator registers a function as a task to be run within the `weave` block.
3.  **Dependency Injection**: `wove` inspects the function signatures. If a task `b` has a parameter named `a`, `wove` assumes `b` depends on the result of task `a` and will wait for `a` to finish before running `b`.
4.  **Concurrent Execution**: Tasks with no unmet dependencies are run concurrently. `wove` automatically handles running sync functions in a thread pool.
5.  **Results**: Once the `async with` block exits, all tasks have completed. You can access results by name (`result['post']`), unpack them (`p, a, c, r = result`), or use the `.final` shortcut for the last task's result.

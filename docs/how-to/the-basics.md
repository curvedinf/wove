# The Basics

The core of Wove's functionality is the `weave` context manager. A `weave` block collects task functions and runs them when Python exits the block. Wove builds a dependency graph from task function signatures: when a task parameter has the same name as another task, Wove passes that upstream task's result into the parameter. Independent tasks run concurrently, dependent tasks wait for their named inputs, and the final task result is available at `w.result.final`.

## Install

Install Wove with `uv`:

```bash
uv add wove
```

Or with `pip`:

```bash
pip install wove
```

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
    def combined(important_text, magic_number):
        return f"{important_text} is {magic_number}!"

    # When the `with` block closes, all tasks are executed.
print(w.result.final)
# >> The meaning of life is 42!
print(f"The magic number was {w.result.magic_number}")
# >> The magic number was 42
print(f'The important text was "{w.result["important_text"]}"')
# >> The important text was "The meaning of life"
```

## Wove's Design Pattern

Wove is designed to be added inline in your existing functions. Since the `weave` context manager is not required to be inside an `async` block, Wove is useful for retrofitting into any IO-bound parallelizable process. For instance, a Django view can load independent database values and API data concurrently before building the template context.

```python
# views.py
import httpx
from django.shortcuts import render
from wove import weave
from .models import Author, Book


async def author_details(request, author_id):
    async with httpx.AsyncClient(timeout=5.0) as client:
        async with weave() as w:
            # These independent database and API calls run concurrently.
            @w.do
            async def author():
                return await Author.objects.values("id", "name", "bio").aget(id=author_id)

            @w.do
            async def book_count():
                return await Book.objects.filter(author_id=author_id).acount()

            @w.do
            async def latest_book():
                return await (
                    Book.objects.filter(author_id=author_id)
                    .order_by("-published_at")
                    .values("id", "title", "published_at")
                    .afirst()
                )

            @w.do
            async def books():
                return [
                    book
                    async for book in (
                        Book.objects.filter(author_id=author_id)
                        .order_by("title")
                        .values("id", "title", "published_at")
                    )
                ]

            @w.do
            async def author_metrics():
                response = await client.get(
                    f"https://metrics.internal/authors/{author_id}"
                )
                response.raise_for_status()
                return response.json()

            # After `books` resolves, each book is enriched concurrently.
            @w.do("books", workers=8, retries=2)
            async def books_with_prices(item):
                response = await client.get(
                    f"https://pricing.internal/books/{item['id']}"
                )
                response.raise_for_status()
                return {**item, "price": response.json()["price"]}

            # When everything is done, create the template context.
            @w.do
            def context(author, book_count, latest_book, author_metrics, books_with_prices):
                return {
                    "author": author,
                    "author_metrics": author_metrics,
                    "book_count": book_count,
                    "latest_book": latest_book,
                    "books": books_with_prices,
                }

    return render(request, "author_details.html", w.result.final)
```

We suggest naming `weave` tasks with nouns instead of verbs. Since `weave` tasks run immediately like inline code and are not meant to be reused as standalone jobs, noun names reinforce that a task represents its output data instead of its action.

## Core API

The two core Wove tools are:

- `weave()`: A context manager used in either a `with` or `async with` block. The block creates the task collection scope, and closing the block runs the collected tasks in dependency order. The `weave` object has a `result` attribute for named task results and a `.final` attribute for the final task result.
- `@w.do`: A decorator that registers a function as a task inside the active `weave` block. Wove accepts both `def` and `async def` tasks; non-async functions run in a background thread pool when needed so they do not block the event loop. Passing an iterable to `@w.do(...)` maps the task over local items. Passing a string such as `@w.do("books")` maps the task over the result named `books` after Wove has produced it.

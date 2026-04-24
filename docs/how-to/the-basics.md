# The Basics

The core of Wove's functionality is the `weave` context manager. It is used in a `with` block to define a list of tasks that will be executed as concurrently and as soon as possible. When Python closes the `weave` block, the tasks are executed immediately based on a dependency graph that Wove builds from the function signatures. Results of a task are passed to any same-named function parameters. The result of the last task that runs are available in `w.result.final`.

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

Wove is designed to be added inline in your existing functions. Since it is not required to be in an `async` block, it is useful for retrofitting into any IO-bound parallelizable process. For instance in a non-async Django view, you can run your database lookups and related code in parallel.

```python
# views.py
import time
from django.shortcuts import render
from wove import weave
from .models import Author, Book


def author_details(request, author_id):
    with weave() as w:
        # `author` and `books` run concurrently
        @w.do
        def author():
            return Author.objects.get(id=author_id)

        @w.do
        def books():
            return list(Book.objects.filter(author_id=author_id))

        # Map the books to a task that updates each of their prices concurrently
        @w.do("books", retries=3)
        def books_with_prices(book):
            book.get_price_from_api()
            return book

        # When everything is done, create the template context
        @w.do
        def context(author, books_with_prices):
            return {
                "author": author,
                "books": books_with_prices,
            }

    return render(request, "author_details.html", w.result.final)
```

We suggest naming `weave` tasks with nouns instead of verbs. Since `weave` tasks are designed to be run immediately like inline code, and not be reused, noun names reinforce the concept that a `weave` task represents its output data instead of its action.

## Core API

The two core Wove tools are:

- `weave()`: An `async` context manager used in either a `with` or `async with` block that creates the execution environment for your tasks. When the `weave` block ends, all tasks will be executed in the order of their dependency graph. The `weave` object has a `result` attribute that contains the results of all tasks and a `.final` attribute that contains the result of the last task.
- `@w.do`: A decorator that registers a function as a task to be run within the `weave` block. It can be used on both `def` and `async def` functions interchangeably, with non-async functions being run in a background thread pool to avoid blocking the event loop. It can optionally be passed an iterable, and if so, the task will be run concurrently for each item in the iterable. It can also be passed a string of another task's name, and if so, the task will be run concurrently for each item in the iterable result of the named task.

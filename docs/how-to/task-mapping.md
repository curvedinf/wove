# Task Mapping

Task mapping is for running the same task once for each item in an iterable. Wove runs those task instances concurrently, collects their results into a list, and passes that list to downstream tasks through the mapped task's normal result name.

Use task mapping when one step naturally fans out over many inputs: URLs to fetch, records to transform, files to parse, IDs to load, or any generated work list.

## Map Over a Local Iterable

Pass an iterable directly to `@w.do(...)` when the inputs are already available before the weave runs. Each mapped task instance receives one value as `item`.

```python
from wove import weave

numbers = [10, 20, 30]

with weave() as w:
    # This block is magically an `async with` block so you can use async functions.
    # Map each item from numbers to the squares function.
    @w.do(numbers)
    async def squares(item):
        return item * item

    # Collect the results.
    @w.do
    def summary(squares):
        return f"Sum of squares: {sum(squares)}"

print(w.result.final)
# Expected output:
# Sum of squares: 1400
```

## Map Over Task Results

Pass the dependency name as a string when the iterable is produced by another task or comes from weave initialization data. If the mapped dependency is a task, Wove waits for that upstream task to finish before starting the mapped instances.

```python
import asyncio
from wove import weave


async def main():
    step = 10
    async with weave(min=10, max=40) as w:
        # Generates the data we want to map over.
        @w.do
        async def numbers(min, max):
            # This scope can read local variables outside the `weave` block, but
            # passing them in as initialization data is cleaner.
            return range(min, max, step)

        # Map each item produced by `numbers` to the `squares` function.
        # Each item's instance of `squares` will run concurrently, and then
        # be collected as a list after all have completed.
        @w.do("numbers")
        async def squares(item):
            return item * item

        # Collects the results.
        # You can mix `async def` and `def` tasks.
        @w.do
        def summary(squares):
            return f"Sum of squares: {sum(squares)}"

    print(w.result.final)


asyncio.run(main())
# Expected output:
# Sum of squares: 1400
```

## Mapping External Callables

Use `merge(callable, iterable)` when the function you want to map is not a Wove task. The callable can be defined inside or outside the `weave` block, and it can be sync or async. Wove runs one copy for each item, collects the returned values into a list, and gives that list back to the task that called it.

This is useful when the fanout is local glue inside one task rather than a named step that downstream tasks should depend on. `merge(...)` must be called inside a task running in an active weave because it uses that weave's executor runtime.

In an async task, await the merged work:

```python
from wove import flatten, merge, weave


def split_words(value):
    return value.split()


with weave() as w:
    @w.do
    def lines():
        return ["hello world", "wove helpers"]

    @w.do
    async def words(lines):
        return flatten(await merge(split_words, lines))

print(w.result.words)
# >> ['hello', 'world', 'wove', 'helpers']
```

In a sync task, call `merge(...)` directly. The task stays normal sync Python even when the callable being merged is async.

```python
from wove import merge, weave


async def fetch_score(customer_id):
    return await scores_api.fetch(customer_id)


with weave(customer_ids=[101, 102, 103]) as w:
    @w.do
    def scores(customer_ids):
        return merge(fetch_score, customer_ids)
```

`merge(...)` accepts the same execution options as `@w.do(...)`: `retries`, `timeout`, `workers`, `limit_per_minute`, `environment`, and the `delivery_*` options used for remote delivery policy.

```python
from wove import merge, weave


with weave(report_ids=[10, 20, 30]) as w:
    @w.do
    async def reports(report_ids):
        return await merge(
            render_report,
            report_ids,
            workers=4,
            retries=2,
            timeout=30.0,
            environment="reports",
            delivery_timeout=60.0,
            delivery_idempotency_key="report:{item}",
            delivery_orphan_policy="requeue",
        )
```

Use `@w.do(iterable)` when the mapped function is part of the weave graph and other tasks should depend on the mapped result by name. Use `merge(...)` when the callable is an external helper and only one task needs its returned list.

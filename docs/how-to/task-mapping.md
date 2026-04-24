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

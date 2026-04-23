# Dependent Task Mapping

You can also map a task over the result of another task or over initialization data by passing the dependency's name as a string to the decorator. This is especially useful when an iterable needs to be generated dynamically. If the mapped dependency is a task, Wove ensures the upstream task completes before starting the mapped tasks.

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

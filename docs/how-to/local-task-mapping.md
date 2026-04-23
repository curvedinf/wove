# Local Task Mapping

You can map a task to a local iterable by passing the iterable to the `@w.do` decorator. Wove will run instances of the task concurrently for each item in the iterable and collect the results as a list after all instances have completed. The result list will be passed to any dependent tasks through the same-named parameter.

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

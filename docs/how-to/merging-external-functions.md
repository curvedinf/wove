# Merging External Functions

Wove provides the `merge` function to dynamically map any callable over an iterable. The callable (typically a function) can be defined inside or outside the `weave` block, and can be `async` or not. A copy of the callable will be run concurrently for each item in the iterable. Used with `await`, a list of results will be returned when all instances have completed.

```python
from wove import weave, merge, flatten


def split(string):
    return string.split(" ")


with weave() as w:
    @w.do
    def strings():
        return ["hello world", "foo bar", "baz qux"]

    @w.do
    async def chopped(strings):
        # Async functions can be within non-async weave blocks.
        # `merge` needs an async function so it can be awaited.
        return flatten(await merge(split, strings))

print(w.result.final)
# >> ['hello', 'world', 'foo', 'bar', 'baz', 'qux']
```

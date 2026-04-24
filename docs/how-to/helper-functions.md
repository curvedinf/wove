# Helper Functions

Wove's helper functions are small utilities that keep common glue code readable inside a weave. They are not required for the core `with weave() as w:` and `@w.do` workflow, but they make fan-out, cleanup, batching, and sync/async interop easier to express without adding throwaway task functions.

Import helpers directly from `wove`:

```python
from wove import batch, denone, flatten, fold, merge, redict, sync_to_async, undict
```

## Data-Shaping

Data-shaping helpers are for the small transformations that often sit between task outputs and downstream tasks. They are plain Python functions, so you can use them inside or outside a weave.

Data-shaping helpers usually appear when a task receives a list, nested list, dictionary, batch, or optional values and needs to shape that data before the next task.

### Flatten Nested Results

Use `flatten(...)` when mapped or merged work returns lists and the downstream task wants one flat list.

```python
from wove import flatten, weave

with weave() as w:
    @w.do
    def chunks():
        return [["alpha", "beta"], ["gamma"]]

    @w.do
    def names(chunks):
        return flatten(chunks)

print(w.result.names)
# >> ['alpha', 'beta', 'gamma']
```

### Split Work Into Groups

Use `fold(a_list, size)` when you know how large each group should be. Use `batch(a_list, count)` when you know how many groups you want.

```python
from wove import batch, fold

items = [1, 2, 3, 4, 5, 6]

print(fold(items, 2))
# >> [[1, 2], [3, 4], [5, 6]]

print(batch(items, 2))
# >> [[1, 2, 3], [4, 5, 6]]
```

Batching fits mapped work when an API accepts groups of records instead of individual records.

```python
from wove import batch, weave

records = list(range(1000))

def upload_records(records):
    return len(records)

with weave() as w:
    @w.do(batch(records, 20))
    def uploaded(item):
        # item is one batch of records
        return upload_records(item)
```

### Move Between Dictionaries And Pairs

Use `undict(...)` when a mapped task should receive one key/value pair at a time. Use `redict(...)` to turn the mapped results back into a dictionary.

```python
from wove import redict, undict, weave

prices = {"basic": 10, "pro": 25}

with weave() as w:
    @w.do(undict(prices))
    def discounted(item):
        name, price = item
        return name, price * 0.9

    @w.do
    def price_table(discounted):
        return redict(discounted)

print(w.result.price_table)
# >> {'basic': 9.0, 'pro': 22.5}
```

### Remove Optional Values

Use `denone(...)` when optional work can return `None` and the next task only wants real values. Other falsy values such as `0`, `False`, and `""` are preserved.

```python
from wove import denone

print(denone([1, None, 0, "", False, 3]))
# >> [1, 0, '', False, 3]
```

## Sync And Async Interop

Wove automatically runs `def` tasks in a thread pool when needed, so most task code does not need an explicit wrapper. Use `sync_to_async(...)` when you have a synchronous function that must be awaited from your own async helper code.

```python
from wove import sync_to_async, weave


def read_file(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


async_read_file = sync_to_async(read_file)

with weave(path="notes.txt") as w:
    @w.do
    async def contents(path):
        return await async_read_file(path)
```

Inside a weave, `sync_to_async(...)` uses Wove's executor context instead of blindly using asyncio's default executor. Wove-aware executor selection matters when Wove is embedded in frameworks that also manage thread pools.

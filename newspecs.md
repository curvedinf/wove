### \#\# Enhanced `@w.do` Parameters

The `@w.do` decorator is enhanced with the following optional parameters for greater control:

  * **`retries: int`**: The number of times to re-run a task if it raises an exception.
  * **`timeout: float`**: The maximum number of seconds a task can run before being cancelled.
  * **`workers: int`**: For mapped tasks, this limits the number of **concurrent** executions to the specified integer.
  * **`limit_per_minute: int`**: For mapped tasks, this throttles their execution to a maximum number per minute. For example, `limit_per_minute=60` would ensure new tasks start no more than once per second.

-----

### \#\# Inheritable Weaves

This feature introduces a class-based method for defining reusable workflows that can be customized inline.

#### **1. Defining a Parent Weave**

Workflows are defined as classes inheriting from `wove.Weave`. Tasks are defined as methods using the **`@Weave.do`** decorator, which is the class-based equivalent of `@w.do` and accepts all the same parameters.

**`reports.py`**

```python
from wove import Weave

class StandardReport(Weave):
    """A reusable Weave template."""

    @Weave.do(retries=2, timeout=5.0)
    async def fetch_data(self, user_id: int):
        # ... logic to fetch from a database or API ...
        return {"id": user_id, "name": "Standard User"}

    @Weave.do
    async def generate_summary(self, fetch_data: dict):
        return f"Report for {fetch_data['name']}"
```

#### **2. Inline Customization**

Pass the `Weave` class to the `weave` context manager. Inside the `with` block, use the instance's `@w.do` decorator to override parent tasks or add new ones.

**Note on Parameter Inheritance**: When overriding a task, the `@w.do` decorator automatically inherits any parameters (like `retries`, `timeout`, etc.) from the parent's `@Weave.do` decorator. You can explicitly provide new values to override the inherited defaults.

**`views.py`**

```python
from wove import weave
from .reports import StandardReport

# This can be a standard synchronous Django view
def admin_report_view(request, user_id: int):
    # Use the synchronous `weave` block for convenience
    with weave(StandardReport) as w:
        # This override inherits `retries=2` from the parent,
        # but overrides `timeout` from 5.0 to 10.0.
        @w.do(timeout=10.0)
        async def fetch_data(user_id: int):
            return {"id": user_id, "name": "Admin"}

    return w.result.generate_summary # Returns "Report for Admin"
```

-----

### \#\# Synchronous Usage

For convenience when integrating into synchronous codebases (like Flask or standard Django), `wove` provides a synchronous context manager.

  * **Syntax**: `with weave(...) as w:`
  * **Behavior**: This block can contain `async def` or `def` tasks just like its async counterpart. Internally, `wove` will manage the `asyncio` event loop, automatically creating, running, and awaiting the entire `async with` block on your behalf.

-----

### \#\# Data-Shaping Helper Functions

`wove` will provide a set of simple, composable helper functions for common data manipulation patterns within your tasks.

  * **`flatten(list_of_lists)`**: Converts a 2D iterable into a 1D list.

      * *Example*: `flatten([[1, 2], [3, 4]])` → `[1, 2, 3, 4]`

  * **`fold(a_list, size)`**: Converts a 1D list into a list of smaller lists of a given size.

      * *Example*: `fold([1, 2, 3, 4], 2)` → `[[1, 2], [3, 4]]`

  * **`undict(a_dict)`**: Converts a dictionary into a list of `[key, value]` pairs.

      * *Example*: `undict({'a': 1, 'b': 2})` → `[['a', 1], ['b', 2]]`

  * **`redict(list_of_pairs)`**: Converts a list of key-value pairs back into a dictionary.

      * *Example*: `redict([['a', 1], ['b', 2]])` → `{'a': 1, 'b': 2}`

  * **`denone(an_iterable)`**: Removes all `None` values from an iterable.

      * *Example*: `denone([1, None, 2, 3])` → `[1, 2, 3]`

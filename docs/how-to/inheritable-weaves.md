# Inheritable Weaves

You can define reusable, overridable workflows by inheriting from `wove.Weave`.

Use inheritable weaves when the graph itself is valuable enough to share. Inline task declaration is still the simplest shape for one-off workflows; inheritable weaves move a reusable shape into a class so callers can run it as-is or override selected tasks.

```python
# In reports.py
from wove import Weave


class StandardReport(Weave):
    @Weave.do(retries=2, timeout=5.0)
    def user_data(self, user_id: int):
        # `user_id` is passed in from the `weave()` call.
        # Wove checks the function's signature at runtime and passes the appropriate data in.
        print(f"Fetching data for user {user_id}...")
        # ... logic to fetch from a database or API ...
        return {"id": user_id, "name": "Standard User"}

    @Weave.do
    def summary(self, user_data: dict):
        return f"Report for {user_data['name']}"
```

To run the reusable `Weave`, pass the class and any required data to the `weave` context manager.

```python
from wove import weave
from .reports import StandardReport

# Any extra keyword arguments you provide to `weave()` are treated as initialization data.
# The initialization data can be consumed by tasks defined in the `Weave` class.
with weave(StandardReport, user_id=123) as w:
    pass

print(w.result.final)
# >> Fetching data for user 123...
# >> Report for Standard User
```

You can also override tasks inline in your `weave` block. It is okay to change the function signature of your override.

```python
from wove import weave
from .reports import StandardReport

# We also pass in `is_admin` because our override needs it.
with weave(StandardReport, user_id=456, is_admin=True) as w:
    # This override has a different signature than StandardReport's version and Wove handles it.
    @w.do(timeout=10.0)
    def user_data(user_id: int, is_admin: bool):
        if is_admin:
            print(f"Fetching data for ADMIN {user_id}...")
            return {"id": user_id, "name": "Admin"}
        # ... regular logic ...
        return {"id": user_id, "name": "Standard User"}

print(w.result.summary)
# >> Fetching data for ADMIN 456...
# >> Report for Admin
```

The same task options apply to inherited tasks and inline overrides.

# Debugging & Introspection

Wove's debugging tools help answer three practical questions: what will run, why will it run in that order, and what happened after it ran.

If a weave is doing the right work in the wrong order, a mapped task is not fanning out the way you expected, a task is slower than expected, or a failure is hard to locate, start by making the execution plan visible.

## Print The Execution Plan

Set `debug=True` when you want Wove to print the task graph before execution starts.

```python
from wove import weave

with weave(debug=True) as w:
    @w.do
    def account():
        return {"id": 1}

    @w.do
    def invoices(account):
        return ["INV-1", "INV-2"]

    @w.do
    def summary(account, invoices):
        return account, invoices
```

The debug report includes:

- Detected tasks, excluding initialization data.
- Each task's dependencies and dependents.
- Execution tiers, where tasks in the same tier can run concurrently.
- Whether each task is `sync` or `async`.
- Mapping information when a task is mapped over a known iterable.

Start with the printed plan when a task starts later than expected. If it appears in a later tier, Wove found a dependency from the task's parameter names.

## Inspect The Graph Programmatically

After the weave exits, `w.execution_plan` contains the same graph information as structured data. Reach for it in tests, generated workflows, or debugging code where printed output is too noisy.

```python
from wove import weave

with weave() as w:
    @w.do
    def user():
        return {"id": 1}

    @w.do
    def profile(user):
        return {"user": user}

print(w.execution_plan["dependencies"])
# >> {'data': set(), 'user': set(), 'profile': {'user'}}

print(w.execution_plan["tiers"])
# >> [['data', 'user'], ['profile']]
```

Use `dependencies` to answer "what does this task wait for?" Use `dependents` to answer "what will this task unblock?" Use `tiers` to understand what Wove can run in parallel.

## Find Unexpected Dependencies

A task depends on another task when one of its parameter names matches that task's name. If a task is running later than expected, inspect its function signature first.

```python
with weave(debug=True) as w:
    @w.do
    def token():
        return "abc"

    @w.do
    def request_headers(token):
        return {"Authorization": f"Bearer {token}"}
```

`request_headers` waits for `token` because it has a `token` parameter. If the parameter was meant to be normal initialization data, pass it into `weave(...)` instead of accidentally naming it after a task.

```python
with weave(token="abc", debug=True) as w:
    @w.do
    def request_headers(token):
        return {"Authorization": f"Bearer {token}"}
```

## Debug Mapped Tasks

When a mapped task uses a local iterable, the debug report shows how many task instances Wove will create.

```python
from wove import weave

ids = [1, 2, 3]

with weave(debug=True) as w:
    @w.do(ids)
    def user(item):
        return {"id": item}
```

The report includes a line like:

```text
- user (sync) [mapped over 3 items]
```

When a task maps over another task's result, Wove may not know the item count until that upstream task has run. In that case the debug report shows the map source name, and the execution tiers show that the mapped task waits for the producer.

```python
with weave(debug=True) as w:
    @w.do
    def ids():
        return [1, 2, 3]

    @w.do("ids")
    def user(item):
        return {"id": item}
```

When a mapped task appears to be skipped or delayed, confirm the source task exists, confirm its name matches the string passed to `@w.do("...")`, and confirm the source returns an iterable.

## Find Slow Tasks

Every result object records task durations in `w.result.timings`. Check timings when the graph is correct but the wall-clock time is not.

```python
import time
from wove import weave

with weave() as w:
    @w.do
    def fast():
        return 1

    @w.do
    def slow():
        time.sleep(0.25)
        return 2

slowest = sorted(w.result.timings.items(), key=lambda item: item[1], reverse=True)
print(slowest[0])
# >> ('slow', 0.25...)
```

Use timings to decide whether to split a task, map it over smaller pieces, raise `max_workers`, or move selected work to a remote task environment.

## Locate Failures

For normal foreground weaves, Wove raises the first task exception from the `with weave()` block. The same exception is also available on `w.result.exception` after the block has unwound.

```python
from wove import weave

try:
    with weave() as w:
        @w.do
        def broken():
            raise ValueError("bad input")
except ValueError:
    print(w.result.exception)
```

When you need to inspect failures without raising on result access, use `error_mode="return"`.

```python
with weave(error_mode="return") as w:
    @w.do
    def broken():
        raise ValueError("bad input")

print(w.result.broken)
# >> bad input
```

## Debug Background Work

Background weaves do not raise failures at the call site because execution continues after the `with` block exits. Use `on_done` to inspect the result when the background weave finishes.

```python
from wove import weave


def on_done(result):
    if result.exception:
        print(f"failed: {result.exception}")
    else:
        print(f"finished: {result.final}")


with weave(background=True, on_done=on_done) as w:
    @w.do
    def expensive_result():
        return 42
```

When background work appears to disappear, remember that the error is not raised where the weave is declared. The callback is the place to observe completion and failure.

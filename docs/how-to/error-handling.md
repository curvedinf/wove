# Error Handling

If any task raises an exception, Wove halts execution, cancels all other running tasks, and re-raises the original exception from the `with weave()` block. This ensures predictable state and allows you to use standard `try...except` blocks.

In background mode, you can inspect the `result.exception` attribute in the `on_done` callback. The attribute is `None` when no exception occurred, or contains the first exception that was raised.

```python
import time
from wove import weave


def on_done_callback(result):
    if result.exception:
        print(f"An error occurred: {result.exception}")
    else:
        print(f"Completed successfully: {result.final}")


with weave(background=True, on_done=on_done_callback) as w:
    @w.do
    def failing_task():
        raise ValueError("Something went wrong")

# >> An error occurred: Something went wrong
```

## Inspect Failed Results Without Raising

By default, Wove raises the task's exception again when you access a failed result. Raising on failed result access keeps normal code honest: if `summary` failed, `w.result.summary`, `w.result["summary"]`, and `w.result.final` should not silently return a partial value.

When you are building a report, dashboard, or test helper, you may want to inspect failures as data instead. Set `error_mode="return"` on the weave or in project configuration. Failed task lookups will return the exception object instead of raising it.

```python
from wove import weave


with weave(error_mode="return") as w:
    @w.do
    def fails():
        raise ValueError("bad input")

value = w.result.fails

assert isinstance(value, ValueError)
assert str(value) == "bad input"
assert w.result.exception is value
```

`result.exception` is always the first exception Wove recorded. `error_mode` only changes what happens when you access a failed task result.

## Configure Error Mode For a Project

If a whole project treats task failures as result values, configure that once with `wove.config(...)`.

```python
import wove

wove.config(error_mode="return")
```

Inspection-heavy workflows benefit from `error_mode="return"` when downstream code needs to decide how to display or group failures. Most application code should stay with the default `error_mode="raise"` because it prevents failed tasks from being mistaken for successful results.

## Backend And Delivery Failures

Tasks routed through `stdio`, a network executor, or a backend adapter still report failures through the same result object. User-code exceptions are returned to the weave when possible. If a remote executor can only send a normalized error payload, Wove wraps it in `EnvironmentExecutionError`.

Delivery problems have their own exception types so you can distinguish task failure from transport failure:

- `DeliveryTimeoutError`: a backend task did not finish before `delivery_timeout`, or stopped sending expected heartbeats.
- `DeliveryOrphanedError`: pending backend work was orphaned while the runtime was stopping or while the executor receiver failed.
- `MissingDispatchFeatureError`: a dispatch-only feature was used without installing `wove[dispatch]`.

```python
from wove import DeliveryTimeoutError, weave


try:
    with weave(environment="reports") as w:
        @w.do(delivery_timeout=10.0)
        def build_report():
            ...
except DeliveryTimeoutError as exc:
    print(f"Report delivery failed: {exc}")
```

Delivery exceptions are recorded the same way as local task exceptions. With the default mode, accessing the failed result raises. With `error_mode="return"`, failed result access returns the exception object.

## Custom Executor Errors

Custom executors should report task failures with a `task_error` frame. Include an `exception` object when the executor is in-process and can safely return one. For process or network boundaries, send a normalized `error` payload instead.

```python
{
    "type": "task_error",
    "run_id": run_id,
    "task_id": task_id,
    "error": {
        "kind": "TimeoutError",
        "message": "Task timed out",
        "source": "transport",
        "retryable": True,
    },
}
```

Wove turns normalized backend error payloads into `EnvironmentExecutionError` when no concrete exception object is available.

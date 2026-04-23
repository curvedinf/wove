# Error Handling

If any task raises an exception, Wove halts execution, cancels all other running tasks, and re-raises the original exception from the `with weave()` block. This ensures predictable state and allows you to use standard `try...except` blocks.

In background mode, you can inspect the `result.exception` attribute in the `on_done` callback. It will be `None` if no exception occurred, or it will contain the first exception that was raised.

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

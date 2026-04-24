# Background Processing

Wove can run an entire weave in the background when the current request, command, or script should continue without waiting for every task result. Background work can stay attached to the current Python process in a thread or move into a detached forked process.

To enable background processing, set `background=True` in the `weave()` call. Wove's background processing supports two modes:

- **Embedded mode (default)**: `weave(background=True)` will run the weave in a new background thread using the `threading` module attached to the current Python process.
- **Forked mode**: `weave(background=True, fork=True)` will run the weave in a new detached Python process. Choose forked mode when the background work should continue after the current process or server worker returns. In an HTTP server worker, for example, the request can finish quickly while the forked Wove process continues processing outside the worker pool.

Embedded mode stays inside the current Python process, so the base install is enough. Forked mode has to carry the weave context into a separate Python process, which requires Wove's optional dispatch serializer:

```bash
pip install "wove[dispatch]"
```

Both modes can be provided an optional `on_done` callback to be executed when the background weave is complete. The callback will receive the `WoveResult` object as its only argument.

```python
import time
from wove import weave


def my_callback(result):
    print(f"Background weave complete! Final result: {result.final}")


# Run in a background thread
with weave(background=True, on_done=my_callback) as w:
    @w.do
    def long_running_task():
        time.sleep(2)
        return "Done!"

print("Main program continues to run...")
# After 2 seconds, the callback will be executed.
```

Before you fork a weave, decide how the child process should report completion. Embedded callbacks can access the current Python process, but forked callbacks run in the child process; use a database, file, queue, or other signaling system when the original process needs the result. Forked mode also serializes the local Python context around the `with` block so the child can preserve task behavior, so keep large local variables out of that scope when you do not want them copied into the fork.

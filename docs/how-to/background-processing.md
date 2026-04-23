# Background Processing

Wove supports running the entire weave in the background, either in a separate thread or a forked process. This is useful for fire-and-forget tasks where you don't want to wait for results.

To enable background processing, set `background=True` in the `weave()` call. Wove's background processing supports two modes:

- **Embedded mode (default)**: `weave(background=True)` will run the weave in a new background thread using the `threading` module attached to the current Python process.
- **Forked mode**: `weave(background=True, fork=True)` will run the weave in a new detached Python process. This is useful for persisting the background process past when the main Python process ends. For instance when running Wove in an HTTP server worker, it is ideal to complete the request as fast as possible and return the worker to the server's pool. Forking Wove allows the background process to continue processing after the worker completes the request and is returned to the pool.

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

There are important considerations when running a weave in the background. Firstly, you are responsible for signaling when a background weave process ends via the callback you provide. With embedded mode, your callback can access the global environment of your Python process, but when using forked mode, your callback will be run from the forked process, so you will need to use a signaling system, database, or file to transmit data back to your original process if that is desired. Secondly, when forking, Wove serializes your entire local Python context to a file to enable all features and ensure maximal compatibility in the remote forked process. This does mean that you must be careful about the size of data stored in local variables in the scope of your `with` statement while using forked mode, as all local variables will be deepcopied to the fork.

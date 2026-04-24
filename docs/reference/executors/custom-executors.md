# Custom Executors

A custom executor is for the cases where a task should leave the current weave process, but Wove should still speak directly to the runtime or service that runs the task. That direct boundary can be an internal worker service, a subprocess protocol, a proprietary scheduler, or a local runtime that does not fit one of Wove's built-in transports.

The executor is the Wove-side transport. A custom executor receives command frames from the weave, such as `run_task` and `cancel_task`, and returns event frames such as `task_result`, `task_error`, or `task_cancelled`. Once the final event arrives, the task result is reintegrated into the same local result object as every other task.

## Interface

Custom executors implement `EnvironmentExecutor`.

```python
class EnvironmentExecutor:
    async def start(self, *, environment_name, environment_config, run_config):
        ...

    async def send(self, frame: dict):
        ...

    async def recv(self) -> dict:
        ...

    async def stop(self):
        ...
```

`start(...)` receives the selected environment name, the environment's `executor_config`, and the run-level Wove configuration. The method opens clients, starts worker processes, or initializes connection pools.

`send(frame)` receives one command frame from Wove. Most executors care about `run_task`, `cancel_task`, and `shutdown`.

The `recv()` method returns one event frame to Wove and should wait until an event is available.

`stop()` releases resources and should make a best effort to stop accepting work.

## Command Frames

Wove sends a `run_task` frame when a task is ready to execute.

```python
{
    "type": "run_task",
    "run_id": "build_report:uuid",
    "task_id": "build_report",
    "callable": build_report,
    "args": {"account": account},
    "delivery": {
        "delivery_timeout": 30.0,
        "delivery_cancel_mode": "best_effort",
        "delivery_orphan_policy": "cancel",
    },
}
```

Wove sends `cancel_task` when cancellation is requested by a timeout, explicit cancellation, or orphan handling.

```python
{
    "type": "cancel_task",
    "run_id": "build_report:uuid",
    "task_id": "build_report",
    "delivery_cancel_mode": "best_effort",
    "delivery_orphan_policy": "cancel",
}
```

Wove sends `shutdown` while the executor runtime is stopping.

## Event Frames

The executor reports task progress with event frames.

| Event | Meaning |
| --- | --- |
| `task_started` | The executor accepted or started the task. |
| `task_result` | The task completed and includes `result`. |
| `task_error` | The task failed and includes either `exception` or a normalized `error` payload. |
| `task_cancelled` | Cancellation completed. |
| `heartbeat` | The task is still alive for heartbeat-based delivery policies. |

For in-process executors, `task_error` can include the original exception object. For process or network executors, send a JSON-safe `error` dictionary with `kind`, `message`, `traceback`, `retryable`, and `source`.

## Minimal Executor

This example runs task frames on local asyncio tasks. It is intentionally small: production executors usually replace `_run_frame(...)` with a client call, process protocol, or service request.

```python
import asyncio
import traceback

import wove
from wove import EnvironmentExecutor, weave


class InlineExecutor(EnvironmentExecutor):
    def __init__(self):
        self.events = asyncio.Queue()
        self.tasks = {}

    async def start(self, *, environment_name, environment_config, run_config):
        self.environment_name = environment_name
        self.environment_config = environment_config
        self.run_config = run_config

    async def send(self, frame):
        if frame["type"] == "run_task":
            task = asyncio.create_task(self._run_frame(frame))
            self.tasks[frame["run_id"]] = task
            return

        if frame["type"] == "cancel_task":
            task = self.tasks.get(frame["run_id"])
            if task is not None:
                task.cancel()
            return

        if frame["type"] == "shutdown":
            for task in self.tasks.values():
                task.cancel()
            return

        raise ValueError(f"Unsupported frame type: {frame['type']}")

    async def recv(self):
        return await self.events.get()

    async def stop(self):
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()

    async def _run_frame(self, frame):
        await self.events.put({
            "type": "task_started",
            "run_id": frame["run_id"],
            "task_id": frame["task_id"],
        })

        try:
            result = frame["callable"](**frame["args"])
            if asyncio.iscoroutine(result):
                result = await result
        except asyncio.CancelledError:
            await self.events.put({
                "type": "task_cancelled",
                "run_id": frame["run_id"],
                "task_id": frame["task_id"],
            })
            return
        except Exception as exc:
            await self.events.put({
                "type": "task_error",
                "run_id": frame["run_id"],
                "task_id": frame["task_id"],
                "error": {
                    "kind": type(exc).__name__,
                    "message": str(exc),
                    "traceback": "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    ),
                    "retryable": False,
                    "source": "task",
                },
            })
            return

        await self.events.put({
            "type": "task_result",
            "run_id": frame["run_id"],
            "task_id": frame["task_id"],
            "result": result,
        })
```

## Configure The Executor

Custom executors are configured by passing an executor instance in the environment definition.

```python
remote_executor = InlineExecutor()

wove.config(
    default_environment="local",
    environments={
        "local": {"executor": "local"},
        "remote": {
            "executor": remote_executor,
            "executor_config": {"region": "us-east-1"},
            "delivery_timeout": 30.0,
        },
    },
)

with weave(environment="local") as w:
    @w.do
    def account_id():
        return "acct_123"

    @w.do(environment="remote")
    def build_report(account_id):
        return {"account_id": account_id, "status": "ready"}

assert w.result.build_report["status"] == "ready"
```

Wove passes `{"region": "us-east-1"}` to `start(...)` as `environment_config`. The weave does not know how the executor uses that configuration; the executor only has to return the normal event frames.

## Contract Checklist

- Return one final event for every accepted `run_task`: `task_result`, `task_error`, or `task_cancelled`.
- Keep `run_id` unchanged on every event so Wove can match the event to the pending task.
- Preserve `task_id` for error messages and debugging output.
- Treat `delivery` settings as runtime policy. Honor cancellation and heartbeat settings when the target system supports them.
- Raise configuration errors from `start(...)` so a bad environment fails before tasks are submitted.
- Raise unsupported command errors from `send(...)` instead of silently dropping frames.

## Related Pages

- [Executors](index.md): frame protocol and built-in executor names.
- [`wove.environment`](../api/wove.environment.md): executor classes and runtime implementation.

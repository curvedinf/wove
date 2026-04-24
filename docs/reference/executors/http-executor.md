# `http` / `https` Executor

`http` sends Wove tasks to a worker service through a normal HTTP request. It fits projects that already have an internal service boundary and want selected weave tasks to run there without adding a queue, workflow engine, or cluster scheduler.

The executor also accepts the name `https`. That alias has the same protocol contract, but it requires the configured URL to use `https://`.

This page uses two separate terms deliberately. The HTTP executor is the Wove-side transport selected by `executor="http"` or `executor="https"`. The worker service is the remote HTTP service that receives Wove frames and returns task events.

## Dependency

HTTP transport uses Python's standard library. The task frame still crosses a network boundary, so Wove needs dispatch serialization:

```bash
pip install "wove[dispatch]"
```

## Configure Wove

```python
import wove

wove.config(
    default_environment="workers",
    environments={
        "workers": {
            "executor": "http",
            "executor_config": {
                "url": "https://workers.internal/wove/tasks",
                "security": "env:WOVE_WORKER_SECRET",
                "timeout": 30.0,
            },
            "delivery_timeout": 35.0,
        }
    },
)
```

The weave only names the environment:

```python
from wove import weave

with weave() as w:
    @w.do(environment="workers")
    def render_report(account_id):
        return build_report(account_id)
```

## Executor Protocol

For each `run_task` or `cancel_task` command, Wove POSTs one JSON body to `executor_config.url`. The body is a Wove command frame with process-unsafe values moved into dispatch fields such as `callable_pickle` and `args_pickle`.

By default, non-local HTTP worker services must use TLS and network executor authentication. Use `https://` plus `security="env:WOVE_WORKER_SECRET"` for the normal path. Plain `http://` without security is allowed only for local development endpoints unless `executor_config.insecure=True` is set explicitly.

The worker service response must be JSON and may be one event frame, a list of event frames, or an object with an `events` list:

```json
{
  "events": [
    {"type": "task_started", "run_id": "...", "task_id": "render_report"},
    {"type": "task_result", "run_id": "...", "task_id": "render_report", "result_pickle": "..."}
  ]
}
```

A `run_task` response should eventually include a terminal frame: `task_result`, `task_error`, or `task_cancelled`. A `cancel_task` response may be empty if cancellation is best-effort.

## Configuration Keys

| Key | Meaning |
| --- | --- |
| `url` | Full HTTP or HTTPS endpoint that receives Wove command frames. Required. |
| `security` | Network executor authentication. Use `env:VARIABLE` for signed requests. |
| `headers` | Extra request headers. |
| `timeout` | Per-request transport timeout in seconds. |
| `insecure` | Allows non-local plaintext or unauthenticated development worker services when true. |

## Related Pages

- [Executors](index.md): frame contract and delivery behavior.
- [`wove.security`](../api/wove.security.md): signed network executor request verification.
- [`grpc` Executor](grpc-executor.md): direct worker-service execution over generic gRPC.
- [`websocket` Executor](websocket-executor.md): persistent bidirectional worker-service execution.

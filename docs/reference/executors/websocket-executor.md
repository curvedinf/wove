# `websocket` Executor

`websocket` keeps a bidirectional connection open between the weave and a worker service. It fits worker services that need to stream task events, send heartbeats, or handle multiple command frames over one connection.

The WebSocket executor is the Wove-side transport selected by `executor="websocket"`. The worker service is the remote WebSocket service that receives command messages and streams event messages back.

## Dependency

The WebSocket executor needs dispatch serialization plus the Python `websockets` package:

```bash
pip install "wove[dispatch]" websockets
```

Wove imports `websockets` only when the `websocket` executor starts.

## Configure Wove

```python
import wove

wove.config(
    default_environment="socket_workers",
    environments={
        "socket_workers": {
            "executor": "websocket",
            "executor_config": {
                "url": "wss://workers.internal/wove",
                "security": "env:WOVE_WORKER_SECRET",
                "open_timeout": 10.0,
            },
            "delivery_heartbeat_seconds": 15.0,
        }
    },
)
```

## Executor Protocol

Wove sends each command frame as one JSON WebSocket message. The worker service returns event frames as JSON messages. A worker message may contain one event frame, a list of event frames, or an object with an `events` list.

The bidirectional shape is useful when the worker service wants to emit `task_started` immediately, send `heartbeat` frames while a task is running, and later send `task_result`, `task_error`, or `task_cancelled`.

By default, non-local WebSocket worker services must use `wss://` and network executor authentication. Wove signs the connection handshake with the configured security helper. Plain `ws://` or unauthenticated non-local targets require `executor_config.insecure=True`.

## Configuration Keys

| Key | Meaning |
| --- | --- |
| `url` | `ws://` or `wss://` endpoint that receives Wove command messages. Required. |
| `security` | Network executor authentication. Use `env:VARIABLE` for signed handshakes. |
| `headers` | Extra connection headers. |
| `open_timeout` | Connection open timeout in seconds. |
| `insecure` | Allows non-local plaintext or unauthenticated development worker services when true. |

## Related Pages

- [Executors](index.md): frame contract and delivery behavior.
- [`wove.security`](../api/wove.security.md): signed network executor handshake verification.
- [`http` / `https` Executor](http-executor.md): direct request/response worker-service execution.
- [`grpc` Executor](grpc-executor.md): direct worker-service execution over generic gRPC.

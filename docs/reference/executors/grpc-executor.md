# `grpc` Executor

`grpc` sends Wove tasks to a worker service through a generic unary gRPC method. It fits projects where worker boundaries are already expressed as gRPC services and Wove should use that network path directly instead of going through a task backend.

The gRPC executor is the Wove-side transport selected by `executor="grpc"`. The worker service is the remote gRPC service that implements the configured method and returns Wove event frames.

## Dependency

The gRPC executor needs dispatch serialization plus the Python gRPC runtime:

```bash
pip install "wove[dispatch]" grpcio
```

Wove imports `grpc` only when the `grpc` executor starts.

## Configure Wove

```python
import wove

wove.config(
    default_environment="grpc_workers",
    environments={
        "grpc_workers": {
            "executor": "grpc",
            "executor_config": {
                "target": "workers.internal:9000",
                "method": "/wove.network_executor.WorkerService/Send",
                "secure": True,
                "metadata": {"x-project": "reports"},
                "security": "env:WOVE_WORKER_SECRET",
                "timeout": 30.0,
            },
        }
    },
)
```

## Executor Protocol

Wove uses gRPC's generic unary call support. The request body is serialized Wove command bytes. The response body is serialized JSON containing one event frame, a list of event frames, or an object with an `events` list.

By default, non-local gRPC worker services must use a secure channel and network executor authentication. Use `secure=True` plus `security="env:WOVE_WORKER_SECRET"` for the normal path. Plaintext or unauthenticated non-local targets require `executor_config.insecure=True`.

That keeps Wove from requiring generated client stubs. The service implementation can be generated, manually registered, or wrapped by an adapter layer, as long as the configured method accepts the raw command bytes and returns raw event bytes.

A `run_task` response should eventually include `task_result`, `task_error`, or `task_cancelled`. Long-running worker services can emit `task_started` first and return the terminal event when the unary call completes. If the worker needs continuous heartbeats or long-lived streaming, prefer the `websocket` executor.

## Configuration Keys

| Key | Meaning |
| --- | --- |
| `target` | gRPC target such as `workers.internal:9000`. Required. |
| `method` | Fully qualified method path. Defaults to `/wove.network_executor.WorkerService/Send`. |
| `secure` | Use `grpc.aio.secure_channel` when true; otherwise use `insecure_channel`. |
| `root_certificates` | Optional root certificate bytes or string for secure channels. |
| `security` | Network executor authentication. Use `env:VARIABLE` for signed metadata. |
| `metadata` | gRPC metadata as a dictionary or sequence of pairs. |
| `timeout` | Per-call timeout in seconds. |
| `insecure` | Allows non-local plaintext or unauthenticated development worker services when true. |

## Related Pages

- [Executors](index.md): frame contract and delivery behavior.
- [`wove.security`](../api/wove.security.md): signed network executor metadata verification.
- [`http` / `https` Executor](http-executor.md): direct worker-service execution over HTTP.
- [`websocket` Executor](websocket-executor.md): persistent bidirectional worker-service execution.

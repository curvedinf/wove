# Executors

Executors are the transport boundary between a weave and the place where a task actually runs. The weave builds a task graph; the executor decides how a single task frame is delivered, executed, cancelled, and reported back.

## Terminology

`dispatch`
: The capability layer that lets Wove serialize task callables, arguments, results, and errors across a process or network boundary.

`execution environment`
: A named Wove configuration selected with `environment=...`. It defines where matching tasks run and which execution defaults apply.

`executor`
: The Wove-side object that receives task frames for an execution environment and reports task events back to the weave.

`event frame`
: A message an executor returns to Wove to report task progress, task result, task error, cancellation, or heartbeat liveness.

`network executor`
: An executor selected with `executor="http"`, `executor="https"`, `executor="grpc"`, or `executor="websocket"`. It sends Wove frames to a remote worker service instead of running the task in the weave process.

`remote worker service`
: The service you own on the other side of a network executor. It implements Wove's executor protocol by receiving command frames, running or forwarding the task, and returning event frames.

## Core Executors

| Executor | Use when |
| --- | --- |
| [`local`](local-executor.md) | Tasks should run in the current Python process. This is the default and fastest path. |
| [`stdio`](stdio-executor.md) | You want a custom process boundary that speaks Wove's JSON-lines frame protocol. |

## Network Executor Names

Network executors are for projects that already have a worker service boundary, but do not need Wove to submit work through a queue, workflow engine, cluster scheduler, or batch system. The remote worker service receives Wove command frames, runs or forwards the task, and returns event frames to Wove.

| Executor value | Worker service shape |
| --- | --- |
| [`http`](http-executor.md) | POST command frames to an HTTP or HTTPS endpoint and receive event frames in the response. |
| [`https`](http-executor.md) | Same as `http`, but the configured URL must use `https://`. |
| [`grpc`](grpc-executor.md) | Call a generic unary gRPC method with serialized command bytes and receive serialized event bytes. |
| [`websocket`](websocket-executor.md) | Keep a bidirectional WebSocket open for command and event frames. |

## Custom Executors

Use a custom executor when Wove should talk directly to a process, service, or runtime that is not covered by the built-in executor names. The custom executor page documents the frame contract, the four-method interface, and the event guarantees Wove expects.

- [Custom Executors](custom-executors.md)

```{toctree}
:maxdepth: 1

local-executor
stdio-executor
http-executor
grpc-executor
websocket-executor
custom-executors
```

## Executor Interface

Every executor follows the same async interface.

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

Method responsibilities:

| Method | Responsibility |
| --- | --- |
| `start(...)` | Open clients, processes, network connections, or other run-scoped resources. |
| `send(frame)` | Accept one runtime command frame. |
| `recv()` | Return one event frame back to Wove. |
| `stop()` | Shut down resources and stop accepting work. |

## Command Frames

Command frames are the messages Wove sends to executors.

### `run_task`

Requests execution for one task.

```python
def greet(name):
    return f"Hello, {name}"


{
    "type": "run_task",
    "run_id": "task_name:uuid",
    "task_id": "greet",
    "callable": greet,
    "args": {"name": "Ada"},
    "delivery": {
        "delivery_timeout": 30.0,
        "delivery_cancel_mode": "best_effort",
        "delivery_idempotency_key": "job:123",
    },
}
```

### `cancel_task`

Asks the executor to cancel one submitted run.

```python
{
    "type": "cancel_task",
    "run_id": "task_name:uuid",
    "task_id": "task_name",
    "delivery_cancel_mode": "best_effort",
    "delivery_orphan_policy": "requeue",
}
```

### `shutdown`

Tells the executor that the runtime is shutting down.

## Event Frames

Event frames are the messages executors return from `recv()`.

| Frame | Meaning |
| --- | --- |
| `task_started` | Executor or worker service accepted or started the task. |
| `task_result` | Task completed successfully and includes `result`. |
| `task_error` | Task failed and includes a normalized `error` payload. |
| `task_cancelled` | Task cancellation completed. |
| `heartbeat` | Optional liveness update for heartbeat-based delivery policies. |

## Executor Errors

Executor errors are normalized so Wove can treat local exceptions, subprocess failures, and network transport failures consistently.

### Normalized Error Frame

Executors should report task failures with `task_error`.

```python
{
    "type": "task_error",
    "run_id": "task_name:uuid",
    "task_id": "task_name",
    "error": {
        "kind": "TimeoutError",
        "message": "Task timed out",
        "traceback": "...",
        "retryable": True,
        "source": "task",
    },
}
```

In-process executors may also include an `exception` object. Process and network executors usually send either a serialized exception payload or a normalized error payload. Wove converts normalized error payloads into `EnvironmentExecutionError` when needed.

### Error Sources

| Source | Meaning |
| --- | --- |
| `task` | User task code raised an exception. |
| `executor` | Executor implementation failed while handling a frame. |
| `transport` | Subprocess or network delivery failed. |
| `config` | Executor or environment configuration is invalid. |

### Public Delivery Exceptions

| Exception | Raised when |
| --- | --- |
| `DeliveryTimeoutError` | `delivery_timeout` is exceeded or heartbeat expiry triggers timeout handling. |
| `DeliveryOrphanedError` | Pending remote work is orphaned while the runtime is stopping. |
| `EnvironmentExecutionError` | A normalized remote error needs to surface as an exception. |
| `MissingDispatchFeatureError` | A dispatch-only feature was used without installing `wove[dispatch]`. |

### Cancellation Contract

Wove sends `cancel_task` when delivery timeout, heartbeat timeout, explicit cancellation, or orphan handling requires cancellation.

Executor responsibility:

- `best_effort`: attempt cancellation if the executor supports it.
- `require_ack`: emit `task_cancelled` only after cancellation is known to have succeeded.
- Orphan policies are hints for shutdown handling and remote cleanup.

## Network Executor Flow

Network executors send Wove's executor protocol directly to a remote worker service you own. The remote worker service is responsible for running the task or forwarding it to whatever local execution model the service owns.

1. Wove serializes the `run_task` command frame.
2. The selected network executor signs or authenticates the request when `executor_config.security` is configured.
3. The network executor sends the frame to the worker service.
4. The worker service verifies the network executor request before decoding task payloads.
5. The worker service returns or streams `task_started`, `task_result`, `task_error`, `task_cancelled`, and optional `heartbeat` frames.
6. Wove resolves the task result from those event frames.

The direct worker-service shape is useful when a project already exposes internal worker APIs and wants Wove to speak to that service directly.

Non-local network executor targets require TLS and authentication by default. The normal configuration is `security="env:WOVE_WORKER_SECRET"`, which signs outgoing requests with a shared secret. Plaintext or unauthenticated non-local targets must set `executor_config.insecure=True` explicitly.

## Dependency Policy

Local in-process execution has no required third-party runtime dependencies. Dispatch features are opt-in because they serialize task callables, arguments, results, and errors across a process or network boundary.

Install dispatch support for forked background execution, `stdio`, network executors, and workers that execute dispatched payloads:

```bash
pip install "wove[dispatch]"
```

- If `executor` is `local`, no optional package is needed.
- If `executor` is `stdio`, `wove[dispatch]` is required.
- If `executor` is `http` or `https`, `wove[dispatch]` is required but no transport package is needed.
- If `executor` is `grpc`, install `wove[dispatch]` and `grpcio`.
- If `executor` is `websocket`, install `wove[dispatch]` and `websockets`.
- Missing dispatch support raises `MissingDispatchFeatureError` with the `wove[dispatch]` install command.
- Missing network transport packages fail with a message that names the package and install command.

## Related Pages

- [`wove.environment`](../api/wove.environment.md): executor classes and runtime implementation.
- [`wove.security`](../api/wove.security.md): shared request signing and verification helpers for network executors.

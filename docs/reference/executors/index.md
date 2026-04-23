# Executors

Executors are the transport boundary between a weave and the place where a task actually runs. The weave builds a task graph; the executor decides how a single task frame is delivered, executed, cancelled, and reported back.

## Choose An Executor

| Executor | Use when |
| --- | --- |
| `local` | Tasks should run in the current Python process. This is the default and fastest path. |
| `stdio` | You want a custom process boundary that speaks Wove's JSON-lines frame protocol. |
| `celery` | You already have Celery workers and a broker. |
| `temporal` | Work should enter a Temporal workflow/task queue. |
| `ray` | Work should run on a Ray cluster. |
| `rq` | Work should run on Redis Queue workers. |
| `taskiq` | Work should run through a Taskiq broker/task. |
| `arq` | Work should run on async Redis ARQ workers. |
| `dask` | Work should run on a Dask distributed scheduler. |
| `kubernetes_jobs` | Each task should run as an isolated Kubernetes Job. |
| `aws_batch` | Each task should run as an AWS Batch job. |
| `slurm` | Each task should run through an HPC Slurm scheduler. |

```{toctree}
:maxdepth: 1

executor-errors
local-executor
stdio-executor
celery
temporal
ray
rq
taskiq
arq
dask
kubernetes-jobs
aws-batch
slurm
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
| `start(...)` | Open clients, processes, callback receivers, queues, or other run-scoped resources. |
| `send(frame)` | Accept one runtime command frame. |
| `recv()` | Return one event frame back to Wove. |
| `stop()` | Shut down resources and stop accepting work. |

## Command Frames

Wove sends these frames to executors.

### `run_task`

Requests execution for one task.

```python
{
    "type": "run_task",
    "run_id": "task_name:uuid",
    "task_id": "task_name",
    "callable": task_func,
    "args": {"name": value},
    "delivery": {
        "delivery_timeout": 30.0,
        "delivery_cancel_mode": "best_effort",
        "delivery_idempotency_key": "job:123",
    },
}
```

### `cancel_task`

Asks the executor or backend to cancel one submitted run.

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

Executors return these frames from `recv()`.

| Frame | Meaning |
| --- | --- |
| `task_started` | Backend accepted or started the task. |
| `task_result` | Task completed successfully and includes `result`. |
| `task_error` | Task failed and includes a normalized `error` payload. |
| `task_cancelled` | Task cancellation completed. |
| `heartbeat` | Optional liveness update for heartbeat-based delivery policies. |

## Remote Callback Flow

Remote task systems usually run outside the weave process. Wove handles that by embedding a callback URL in each remote payload.

1. `RemoteAdapterEnvironmentExecutor` starts a callback receiver.
2. The adapter submits a JSON-safe payload to the backend.
3. A backend worker calls `wove.integrations.worker.run(payload)` or `await wove.integrations.worker.arun(payload)`.
4. The worker posts event frames back to the callback URL.
5. The executor runtime receives those frames and resolves the task result.

For workers on another host or network, set a reachable URL explicitly:

```python
wove.config(
    environments={
        "reports": {
            "executor": "celery",
            "executor_config": {
                "broker_url": "redis://redis:6379/0",
                "task_name": "myapp.wove_task",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        },
    },
)
```

`callback_host` and `callback_port` control where the local receiver binds. `callback_url` is what remote workers receive in the payload.

## Dependency Policy

Adapter modules ship with Wove. Backend libraries do not become required package dependencies.

- If `executor` is `local` or `stdio`, no backend package is needed.
- If `executor` is a task-system adapter, Wove checks for that backend package at executor startup.
- Missing packages fail with a message that names the package and install command.

## Related Pages

- [Executor Errors](executor-errors.md): error payloads, timeouts, and cancellation behavior.
- [`wove.environment`](../api/wove.environment.md): executor classes and runtime implementation.
- [`wove.remote`](../api/wove.remote.md): callback server and payload helpers.
- [`wove.integrations`](../api/wove.integrations.md): adapter registry and base interface.

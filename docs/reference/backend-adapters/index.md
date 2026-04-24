# Backend Adapters

Use a backend adapter when a Wove task should run inside infrastructure your project already depends on: a queue, workflow engine, cluster, batch system, or scheduler. The weave stays inline in Python, but the selected task is handed to Celery, Temporal, Ray, Kubernetes, AWS Batch, Slurm, or another supported backend for execution.

Backend adapters are different from network executors. A network executor talks directly to a Wove-compatible worker service over HTTP, gRPC, or WebSocket. A backend adapter lets an existing task system own the delivery path, worker placement, scheduling behavior, and operational controls that system already provides.

## What The Adapter Does

A backend adapter is the small Wove layer that submits one selected task to one backend. The task code does not need to import Celery, Temporal, Ray, or the selected system. The environment configuration names the backend once, and the weave only refers to that environment.

```python
import wove
from wove import weave

wove.config(
    default_environment="default",
    environments={
        "default": {"executor": "local"},
        "reports": {
            "executor": "celery",
            "executor_config": {
                "broker_url": "redis://redis:6379/0",
                "task_name": "myapp.wove_task",
            },
            "delivery_timeout": 30.0,
        },
    },
)

with weave() as w:
    @w.do
    def account():
        return load_account()

    @w.do(environment="reports")
    def report(account):
        return build_report(account)
```

In that example, `account` runs locally and `report` is submitted through Celery. The task still appears in the same Wove result object after the backend worker reports completion to Wove.

## Callback Lifecycle

Backend adapters use callbacks because the backend, not Wove, owns the worker process that eventually runs the task. The weave process cannot rely on a direct return value from Celery, Temporal, AWS Batch, Slurm, or another backend. Instead, Wove opens a callback receiver, submits a payload that includes the callback address, and waits for worker events to arrive back at that receiver.

The callback receiver is hosted by Wove in the process running the weave. It listens for `POST` requests at `/wove/events/{callback_token}`. Application frameworks do not need to define that route unless the project intentionally proxies traffic through one.

### Task Payload Out

Task exfiltration starts when a task routed to a backend adapter becomes ready in the local dependency graph. At that point, all upstream Wove dependencies have resolved, so Wove can serialize the selected callable and its concrete arguments into one backend payload.

```json
{
  "version": 1,
  "adapter": "celery",
  "callback_url": "http://web:9010/wove/events/shared-secret",
  "run_id": "...",
  "task_id": "report",
  "task_name": "report",
  "callable_pickle": "...",
  "args_pickle": "...",
  "delivery": {
    "delivery_timeout": 30.0
  }
}
```

`callable_pickle` is the selected Python callable. `args_pickle` is the dictionary of resolved arguments Wove would have passed to the callable locally. These fields require `wove[dispatch]` because the callable and its data are crossing a process or network boundary.

The adapter receives this payload and submits it unchanged to the backend. The adapter may add backend-specific delivery metadata such as a Celery queue, a Kubernetes job name, an AWS Batch queue, or a Slurm partition, but the Wove payload itself remains the unit the worker must execute.

### Worker Execution

The backend worker receives the payload through whatever mechanism the selected system provides. The worker then calls Wove's worker entrypoint:

```python
from wove.integrations.worker import arun, run
```

Synchronous workers call `run(payload)`. Async workers call `await arun(payload)`. The entrypoint decodes the callable and arguments, runs the callable, and serializes the result or exception into callback events.

The backend job's own return value is not the task result consumed by the weave. The backend return value only satisfies the backend system. Wove consumes the callback event posted by the worker entrypoint.

### Result Events Back

Result infiltration is the reverse path. The worker posts event frames to the `callback_url` embedded in the payload:

- `task_started` marks the remote task as running.
- `task_result` carries a successful return value.
- `task_error` carries a task exception or normalized remote error.
- `task_cancelled` marks the task as cancelled.

Wove's callback receiver deserializes those frames and feeds them back into the same executor event stream used by local, stdio, and network executors. The original weave then resolves the pending task, makes the returned value available to downstream tasks, or raises according to the weave's error policy.

### Callback Addressing

`callback_host` and `callback_port` configure where Wove binds its callback server. `callback_url` configures the URL embedded in submitted payloads. The worker-facing URL must route to the Wove callback server from the worker's network location.

For local development, Wove can generate a callback URL from its bound host and port. For containers, clusters, and cloud workers, set `callback_url` explicitly:

```python
"executor_config": {
    "callback_host": "0.0.0.0",
    "callback_port": 9010,
    "callback_token": "shared-secret",
    "callback_url": "http://web:9010/wove/events/shared-secret",
}
```

The backend owns queueing, scheduling, backend-level retries, worker placement, job lifecycle, and cluster execution. Wove owns the payload shape, callback receiver, event delivery, task result reintegration, and delivery errors seen by the weave.

## Install Only What The Environment Uses

Local Wove does not require backend packages. Backend adapters are opt-in because they move task callables, arguments, results, and errors across a process or network boundary.

Install Wove dispatch support in the process that submits the task and in the worker environment that executes the payload. Then install the backend package for the adapter you selected.

```bash
pip install "wove[dispatch]" celery
```

The adapter code ships with Wove, but the backend libraries remain optional. If an environment selects `executor="celery"` without Celery installed, Wove fails when that environment starts and names the missing package.

## Built-In Adapters

Each built-in adapter page describes one supported system.

| Adapter | Use when |
| --- | --- |
| [Celery](celery.md) | Work should enter Celery workers through a broker. |
| [Temporal](temporal.md) | Work should enter a Temporal task queue or workflow-owned worker. |
| [Ray](ray.md) | Work should run on a Ray cluster. |
| [RQ](rq.md) | Work should run on Redis Queue workers. |
| [Taskiq](taskiq.md) | Work should run through a Taskiq broker and task name. |
| [ARQ](arq.md) | Work should run on async Redis ARQ workers. |
| [Dask](dask.md) | Work should run on Dask distributed workers. |
| [Kubernetes Jobs](kubernetes-jobs.md) | Each task should run as an isolated Kubernetes Job. |
| [AWS Batch](aws-batch.md) | Each task should run as an AWS Batch job. |
| [Slurm](slurm.md) | Work should run through an HPC Slurm scheduler. |

## Custom Backend Adapters

Use a custom backend adapter when your project already has a task system that should own queueing, scheduling, retries, worker placement, or batch execution, and Wove only needs to submit selected task payloads into that system.

- [Custom Backend Adapters](custom-backend-adapters.md)

```{toctree}
:maxdepth: 1
:hidden:

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
custom-backend-adapters
```

## Related Pages

- [Remote Task Environments](../../how-to/remote-task-environments.md): choosing local execution, network executors, and backend adapters.
- [Executors](../executors/index.md): executor frame contract and delivery errors.
- [`wove.integrations`](../api/wove.integrations.md): adapter registry, base interface, and worker entrypoints.
- [`wove.backend`](../api/wove.backend.md): backend callback transport and dispatch payload helpers.

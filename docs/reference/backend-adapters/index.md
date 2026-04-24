# Backend Adapters

Use a backend adapter when a Wove task should run inside infrastructure your project already depends on: a queue, workflow engine, cluster, batch system, or scheduler. The weave stays inline in Python, but the selected task is handed to Celery, Temporal, Ray, Kubernetes, AWS Batch, Slurm, or another supported backend for execution.

That is different from a network executor. A network executor talks directly to a Wove-compatible worker service over HTTP, gRPC, or WebSocket. A backend adapter lets an existing task system own the delivery path, worker placement, scheduling behavior, and operational controls that system already provides.

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

In that example, `account` runs locally and `report` is submitted through Celery. The task still appears in the same Wove result object after the backend worker returns its event frame.

## Execution Flow

Backend adapters use a callback flow because the selected backend usually runs work outside the weave process.

1. Wove serializes the selected task into a backend payload.
2. The adapter submits that payload to the selected backend.
3. A backend worker executes the payload with `wove.integrations.worker.run(payload)` or `await wove.integrations.worker.arun(payload)`.
4. The worker posts `task_started`, `task_result`, `task_error`, or `task_cancelled` back to Wove's callback URL.
5. Wove resolves the task result in the original weave.

The backend owns the middle of that flow: queueing, scheduling, retries outside Wove, worker placement, job lifecycle, or cluster execution. Wove owns the task payload shape, callback receiver, result delivery, and delivery errors seen by the weave.

## Install Only What The Environment Uses

Local Wove does not require backend packages. Backend adapters are opt-in because they move task callables, arguments, results, and errors across a process or network boundary.

Install Wove dispatch support in the process that submits the task and in the worker environment that executes the payload. Then install the backend package for the adapter you selected.

```bash
pip install "wove[dispatch]" celery
```

The adapter code ships with Wove, but the backend libraries remain optional. If an environment selects `executor="celery"` without Celery installed, Wove fails when that environment starts and names the missing package.

## Built-In Adapters

Choose the page for the system your project already runs.

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

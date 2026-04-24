# Remote Task Environments

Wove can keep quick work in the current Python process while sending selected long-running or infrastructure-sensitive work to a worker service, queue, workflow engine, cluster, or scheduler.

Remote task environments route selected tasks to another execution boundary and bring their results back into the same weave.

That matters when the shape of the workflow belongs inline, but production execution belongs somewhere else. A web request can keep lightweight lookups in-process, hand report generation to an internal worker service or task backend, and keep those routing choices out of task code.

Environments are the named execution profiles that make that possible. `wove.config(...)` defines which environment is the default and which environments route work through network executors or backend adapters.

## Install What Remote Execution Needs

If every task runs in the current Python process, the base `wove` install is enough. Remote task environments are different: Wove has to carry task callables, arguments, results, and errors across a process or network boundary. The command below adds the serializer Wove uses for forked background work, `stdio` worker processes, network executors, backend adapters, and workers that execute dispatched payloads.

```bash
pip install "wove[dispatch]"
```

That command only adds Wove's dispatch serializer. Some executors need an additional transport or backend package. The `http` and `https` executors use the Python standard library. The `grpc` executor needs `grpcio`; the `websocket` executor needs `websockets`. If an environment uses a backend adapter, install that backend's Python package anywhere Wove submits the task and anywhere backend workers execute Wove payloads. For Celery, that means installing both Wove dispatch support and Celery:

```bash
pip install "wove[dispatch]" celery
```

## Start with a Local Default

Most projects should keep local execution as the default. That preserves the normal `with weave() as w:` workflow while giving the project one place to define shared execution policy.

```python
import wove

wove.config(
    default_environment="default",
    environments={
        "default": {
            "executor": "local",
            "max_workers": 64,
            "retries": 1,
            "timeout": 30.0,
        }
    },
    error_mode="raise",
)
```

## Add a Remote Task Environment

A remote task environment is a named execution profile for work that should leave the current Python process. It describes which external task system matching tasks should use and what delivery policy they should follow.

```python
import wove

wove.config(
    default_environment="default",
    environments={
        "default": {"executor": "local", "max_workers": 64},
        "reports": {
            "executor": "temporal",
            "executor_config": {"task_queue": "wove-reports"},
            "retries": 3,
            "timeout": 120.0,
            "delivery_timeout": 20.0,
            "delivery_cancel_mode": "best_effort",
        },
    },
)
```

The weave code does not need to know how Temporal, Celery, Ray, or another backend is wired. It only refers to the environment name.

## Route the Task That Needs It

Environment routing can happen at the whole-weave level or at the task level. Task-level routing is useful when most work should stay local but one step belongs on queue, workflow, cluster, batch, or scheduler infrastructure.

```python
from wove import weave

with weave(environment="default") as w:
    @w.do
    def fast_lookup():
        ...

    @w.do(environment="reports")
    def long_running_step(fast_lookup):
        ...
```

## Keep Configuration in `wove_config.py`

Configuration can live in startup code, but larger projects usually benefit from one project-level file. Calling `wove.config()` with no arguments attempts to autoload `wove_config.py` from the current working directory or one of its parents.

```python
# wove_config.py
WOVE = {
    "default_environment": "default",
    "environments": {
        "default": {"executor": "local"},
        "reports": {
            "executor": "stdio",
            "executor_config": {"command": ["python", "-m", "my_worker"]},
            "retries": 3,
        },
    },
    "max_workers": 64,
    "delivery_timeout": 15.0,
}
```

```python
import wove

wove.config()  # autoload
# or:
# wove.config(config_file="/abs/path/to/custom_config.py")
```

## Resolution Order

Wove resolves environment names from the most specific declaration outward:

1. Task-level `@w.do(environment="...")`
2. Weave-level `weave(environment="...")`
3. `wove.config(default_environment="...")`
4. Built-in fallback: `"default"`

Effective task settings follow the same principle. Values closest to the task win:

1. Task-level `@w.do(...)` values
2. Weave-level values for weave-scoped settings (`max_workers`, `background`, `fork`, `error_mode`)
3. Selected environment values
4. Global defaults from `wove.config(...)`
5. Built-in defaults

## Direct Worker Services

When a project already has its own worker service, a network executor lets Wove talk to that service directly. The network executor is the Wove-side transport selected by `executor="http"`, `executor="grpc"`, or `executor="websocket"`. The worker service is the remote process that receives Wove command frames, runs or forwards the task, and returns Wove event frames.

```python
wove.config(
    default_environment="default",
    environments={
        "default": {"executor": "local"},
        "workers": {
            "executor": "http",
            "executor_config": {
                "url": "https://workers.internal/wove/tasks",
                "security": "env:WOVE_WORKER_SECRET",
            },
            "delivery_timeout": 30.0,
        },
    },
)
```

That shape is useful when the project needs a direct service boundary, not backend-owned queueing or scheduling. The built-in network executors are `http`, `https`, `grpc`, and `websocket`. For non-local worker services, Wove expects TLS and a `security` setting unless `insecure=True` is set explicitly for development.

## Executor Notes

The built-in executor names are `local`, `stdio`, `http`, `https`, `grpc`, `websocket`, `celery`, `temporal`, `ray`, `rq`, `taskiq`, `arq`, `dask`, `kubernetes_jobs`, `aws_batch`, and `slurm`.

Choose `stdio` when you want a custom process boundary without a queue or workflow engine. Wove launches a JSON-lines worker process and sends task frames through that process boundary, so the environment running it needs the dispatch serializer from `wove[dispatch]`. If `executor_config.command` is omitted, Wove runs `python -m wove.stdio_worker`.

Backend adapters use a callback shape. Wove starts a small callback receiver, submits the task payload to the backend, and waits for the backend worker to post `task_started`, `task_result`, `task_error`, or `task_cancelled` frames back to the weave.

The backend worker should call one of Wove's provided worker entrypoints:

```python
from wove.integrations.worker import arun, run
```

Use `run(payload)` from synchronous workers such as Celery or RQ. Use `await arun(payload)` from async workers such as Taskiq, ARQ, or async Temporal activities.

Backend workers must be able to reach the callback URL. For workers on another host or network, configure a stable token and a public/internal route back to the Wove process:

```python
wove.config(
    default_environment="reports",
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

Wove checks remote execution dependencies when the environment starts. If the dispatch serializer, selected network transport package, or selected backend library is missing, startup fails with an install hint before the task is submitted. Referencing an unknown environment name raises `NameError` at runtime.

Network executor setup varies by transport. Start with the transport your worker service already exposes:

- [HTTP/HTTPS Executor](../reference/executors/http-executor.md): direct request/response worker services.
- [gRPC Executor](../reference/executors/grpc-executor.md): generic unary gRPC worker services.
- [WebSocket Executor](../reference/executors/websocket-executor.md): bidirectional worker services that stream events.

Backend setup varies by system. Start with the page for the system your project already runs:

- [Celery](../reference/backend-adapters/celery.md): broker-backed worker pools.
- [Temporal](../reference/backend-adapters/temporal.md): workflow/task-queue execution.
- [Ray](../reference/backend-adapters/ray.md): Ray cluster execution.
- [RQ](../reference/backend-adapters/rq.md): Redis Queue workers.
- [Taskiq](../reference/backend-adapters/taskiq.md): async task queues with explicit tasks.
- [ARQ](../reference/backend-adapters/arq.md): async Redis workers.
- [Dask](../reference/backend-adapters/dask.md): distributed Python schedulers.
- [Kubernetes Jobs](../reference/backend-adapters/kubernetes-jobs.md): isolated pod-per-task execution.
- [AWS Batch](../reference/backend-adapters/aws-batch.md): managed batch compute jobs.
- [Slurm](../reference/backend-adapters/slurm.md): HPC batch scheduling.

# Advanced/Remote Execution Environments

Wove can execute tasks inside the current Python process or hand selected work to an existing task system such as Celery, Temporal, Ray, or Dask.

This keeps the weave itself inline and readable while letting production workloads use the infrastructure they already depend on. A web request can keep quick local work in-process, send long-running work to a queue or workflow engine, and keep those routing choices out of task code.

Environments are the named execution profiles that make that possible. `wove.config(...)` defines which environment is the default and which environments route work through remote executors.

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

## Add a Remote Environment

A remote environment is a named execution profile. It describes where matching tasks should run and what delivery policy they should use.

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

Environment routing can happen at the whole-weave level or at the task level. Task-level routing is useful when most work should stay local but one step belongs on remote infrastructure.

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
            "executor_config": {"command": ["python", "-m", "my_gateway"]},
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

## Remote Executor Notes

The built-in executor names are `local`, `stdio`, `celery`, `temporal`, `ray`, `rq`, `taskiq`, `arq`, `dask`, `kubernetes_jobs`, `aws_batch`, and `slurm`.

`stdio` launches a JSON-lines gateway process. If `executor_config.command` is omitted, Wove runs `python -m wove.gateway`.

Task-system adapters use a remote callback shape. Wove starts a small callback receiver, submits the task payload to the backend, and waits for the backend worker to post `task_started`, `task_result`, `task_error`, or `task_cancelled` frames back to the weave.

The backend worker should call one of Wove's provided worker entrypoints:

```python
from wove.integrations.worker import arun, run
```

Use `run(payload)` from synchronous workers such as Celery or RQ. Use `await arun(payload)` from async workers such as Taskiq, ARQ, or async Temporal activities.

Remote workers must be able to reach the callback URL. For workers on another host or network, configure a stable token and a public/internal route back to the Wove process:

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

Adapter backend libraries are optional dependencies. If an adapter is selected but its dependency is missing, startup fails with an install hint. Referencing an unknown environment name raises `NameError` at runtime.

Each backend has its own setup shape. Use the page for the system your project already runs:

- [Celery](../reference/executors/celery.md): broker-backed worker pools.
- [Temporal](../reference/executors/temporal.md): workflow/task-queue execution.
- [Ray](../reference/executors/ray.md): Ray cluster execution.
- [RQ](../reference/executors/rq.md): Redis Queue workers.
- [Taskiq](../reference/executors/taskiq.md): async task queues with explicit tasks.
- [ARQ](../reference/executors/arq.md): async Redis workers.
- [Dask](../reference/executors/dask.md): distributed Python schedulers.
- [Kubernetes Jobs](../reference/executors/kubernetes-jobs.md): isolated pod-per-task execution.
- [AWS Batch](../reference/executors/aws-batch.md): managed batch compute jobs.
- [Slurm](../reference/executors/slurm.md): HPC batch scheduling.

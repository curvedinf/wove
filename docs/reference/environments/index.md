# Environments

An environment is a persistent named execution profile. Weaves stay lightweight and non-persistent; environments hold the durable choices about where work runs, how much concurrency is allowed, and which delivery policy applies.

## When To Use Environments

Use an environment when a task needs behavior that should be configured once for the project instead of repeated in every weave:

- Keep most tasks local but send one task to a queue, workflow engine, cluster, or batch scheduler.
- Apply shared defaults such as `retries`, `timeout`, or `max_workers`.
- Keep backend configuration out of task code.
- Switch infrastructure by changing `wove.config(...)` rather than rewriting decorators.

## Definition Shape

Every environment is a plain dictionary. Every key is optional.

```python
{
    "executor": "local" | "stdio" | "celery" | "temporal" | "ray" | ...,
    "executor_config": { ... },
    "max_workers": 32,
    "background": False,
    "fork": False,
    "retries": 1,
    "timeout": 30.0,
    "workers": 20,
    "limit_per_minute": 600,
    "max_pending": 10000,
    "error_mode": "raise",
    "delivery_timeout": 20.0,
    "delivery_idempotency_key": "job:{order_id}",
    "delivery_cancel_mode": "best_effort",
    "delivery_heartbeat_seconds": 5.0,
    "delivery_max_in_flight": 1000,
    "delivery_orphan_policy": "requeue",
}
```

## Executor Selection

`executor` decides where task frames are sent.

- `local`: run tasks in the current Python process.
- `stdio`: run tasks through a JSON-lines subprocess gateway.
- `celery`, `temporal`, `ray`, `rq`, `taskiq`, `arq`, `dask`, `kubernetes_jobs`, `aws_batch`, `slurm`: submit tasks to a remote task system and receive callback frames.
- `EnvironmentExecutor` instance: custom executor object.

`executor_config` belongs to the executor. Wove treats it as backend-specific data and passes it to the selected executor during startup.

## Execution Defaults

These settings affect normal task execution and use the same naming style as `weave(...)` and `@w.do(...)` arguments.

| Key | Effect |
| --- | --- |
| `max_workers` | Thread pool size for sync task execution. |
| `background` | Default background execution mode. |
| `fork` | Default forked background mode. |
| `retries` | Default retry count. |
| `timeout` | Default task timeout in seconds. |
| `workers` | Parallelism cap for mapped tasks. |
| `limit_per_minute` | Launch-rate cap for mapped tasks. |
| `max_pending` | Pending-work cap. |
| `error_mode` | `raise` or `return`. |

## Delivery Defaults

Delivery settings only affect executor delivery behavior, so their names use the `delivery_` prefix.

| Key | Effect |
| --- | --- |
| `delivery_timeout` | Maximum time to wait for a remote delivery result. |
| `delivery_idempotency_key` | Optional dedupe key or format string. |
| `delivery_cancel_mode` | `best_effort` or `require_ack`. |
| `delivery_heartbeat_seconds` | Expected heartbeat interval before timeout handling. |
| `delivery_max_in_flight` | In-flight dispatch cap for an environment. |
| `delivery_orphan_policy` | `fail`, `cancel`, `requeue`, or `detach`. |

## Resolution Order

Wove resolves the environment name from the most specific declaration outward:

1. Task-level `@w.do(environment="...")`
2. Weave-level `weave(environment="...")`
3. `wove.config(default_environment="...")`
4. Built-in fallback: `"default"`

Task settings use the same principle:

1. Task-level decorator arguments.
2. Weave-level settings where applicable.
3. Selected environment settings.
4. Global defaults from `wove.config(...)`.
5. Built-in defaults.

## Project Config File

`wove.config()` with no arguments attempts to load `wove_config.py` from the current working directory or one of its parents. The file is optional, and every setting inside it is optional.

```python
# wove_config.py
WOVE = {
    "default_environment": "default",
    "environments": {
        "default": {"executor": "local"},
        "reports": {
            "executor": "celery",
            "executor_config": {
                "broker_url": "redis://redis:6379/0",
                "task_name": "myapp.wove_task",
            },
            "timeout": 120.0,
            "delivery_timeout": 30.0,
        },
    },
}
```

## Validation And Errors

- Unknown environment names raise `NameError` when a weave tries to use them.
- Invalid `delivery_cancel_mode` values raise `ValueError`.
- Invalid `delivery_orphan_policy` values raise `ValueError`.
- Unknown executor names raise `ValueError` during executor construction.
- Missing optional backend libraries raise a startup error with an install hint.

## Related Pages

- [`wove.runtime`](../api/wove.runtime.md): process-wide configuration implementation.
- [Executors](../executors/index.md): executor names, frame contract, and remote callback behavior.
- [Advanced/Remote Execution Environments](../../how-to/advanced-remote-execution-environments.md): guided setup narrative.

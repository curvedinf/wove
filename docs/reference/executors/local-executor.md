# `local` Executor

`local` runs tasks in the current Python process. It is the default executor and the best choice until a task specifically needs another process, host, queue, cluster, or scheduler.

## Use When

- You want the fastest startup path.
- Tasks are I/O-bound or lightweight enough to run in the submitting process.
- You do not need a broker, worker pool, cluster, or durable scheduler.
- You are developing locally and want backend routing to be opt-in per task.

## Configure Wove

```python
import wove

wove.config(
    default_environment="default",
    environments={
        "default": {
            "executor": "local",
            "max_workers": 64,
        }
    },
)
```

## Behavior

- Sync and async tasks are supported directly.
- Task results and exceptions stay in-process.
- Cancellation uses Python task cancellation for active local runs.
- No external services or optional backend packages are required.

## Limits

`local` is not durable. If the process exits, running work exits with it. Use a network executor or backend adapter when work needs to run on separate infrastructure; use a backend adapter when another system should own durability or scheduling.

## Related Pages

- [Environments](../environments/index.md): setting local as a default environment.
- [Executors](index.md): executor frame contract.

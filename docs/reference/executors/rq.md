# RQ

RQ is for Redis Queue deployments where selected Wove tasks should run in an existing Python worker queue.

## Use When

- Your project already runs RQ workers.
- A simple Redis-backed queue is enough for the task.
- Workers can import Wove and application code.

## Execution Shape

1. Wove enqueues `wove.integrations.worker.run(payload)`.
2. An RQ worker executes that function.
3. The worker posts Wove event frames back to the callback URL.

## Dependency

```bash
pip install rq
```

## Configure Wove

```python
import wove

wove.config(
    default_environment="rq",
    environments={
        "rq": {
            "executor": "rq",
            "executor_config": {
                "redis_url": "redis://redis:6379/0",
                "queue_name": "wove",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

You can pass an existing RQ queue as `executor_config["queue"]`. If `queue` is omitted, Wove creates one from `redis_url` and `queue_name`.

## Worker

Start a normal RQ worker against the same queue.

```bash
rq worker wove
```

## Options

| Key | Effect |
| --- | --- |
| `queue` | Existing RQ queue. |
| `redis_url` | Redis URL used when Wove creates the queue. |
| `queue_name` | Queue name. Defaults to `default`. |
| `enqueue_options` | Extra keyword arguments passed to `queue.enqueue(...)`. |

## Related Pages

- [Executors](index.md): remote callback flow.
- [`wove.integrations`](../api/wove.integrations.md): worker entrypoints.

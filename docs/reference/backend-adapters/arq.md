# ARQ

ARQ is for async Redis worker deployments. Wove enqueues a named ARQ function with the payload, and that function posts completion back through Wove's callback URL.

## Use When

- Your project already runs ARQ workers.
- Worker code is async and Redis-backed.
- You want a named worker function to execute Wove payloads.

## Execution Shape

1. Wove creates or uses an ARQ pool.
2. Wove calls `enqueue_job(function_name, payload, ...)`.
3. The ARQ worker function calls `await wove.integrations.worker.arun(payload)`.
4. The worker posts Wove event frames back to the callback URL.

## Dependency

Install dispatch support and ARQ in the submitting process and in ARQ workers.

```bash
pip install "wove[dispatch]" arq
```

## Configure Wove

```python
import wove
from arq.connections import RedisSettings

wove.config(
    default_environment="arq",
    environments={
        "arq": {
            "executor": "arq",
            "executor_config": {
                "redis_settings": RedisSettings(host="redis"),
                "function_name": "myapp_wove_task",
                "queue_name": "wove",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

You can pass an existing ARQ pool as `executor_config["pool"]`. If `pool` is omitted, Wove creates one with `redis_settings`.

## Worker Function

```python
from wove.integrations.worker import arun


async def myapp_wove_task(ctx, payload):
    return await arun(payload)


class WorkerSettings:
    functions = [myapp_wove_task]
    queue_name = "wove"
```

## Options

| Key | Effect |
| --- | --- |
| `pool` | Existing ARQ Redis pool. |
| `redis_settings` | Settings used when Wove creates the pool. |
| `function_name` | ARQ function name. Defaults to `wove_run_backend_payload`. |
| `queue_name` | Optional ARQ queue name. |
| `enqueue_options` | Extra keyword arguments passed to `enqueue_job(...)`. |

## Related Pages

- [Backend Adapters](index.md): callback flow and adapter responsibilities.
- [`wove.integrations`](../api/wove.integrations.md): worker entrypoints.

# Celery

Celery is for projects that already run broker-backed worker pools and want selected Wove tasks to enter those workers instead of running in the web or orchestration process.

## Use When

- Your project already has a Celery broker and workers.
- Work should leave the submitting process quickly.
- You want Wove's inline dependency graph but Celery's worker deployment model.

## Execution Shape

1. Wove submits the payload with `app.send_task(...)`.
2. A Celery worker runs the configured task name.
3. That task calls `wove.integrations.worker.run(payload)`.
4. The worker posts Wove completion events back to the callback URL embedded in the payload.

## Dependency

Install dispatch support and Celery in the process that submits work and in the workers that execute it.

```bash
pip install "wove[dispatch]" celery
```

## Configure Wove

```python
import wove

wove.config(
    default_environment="celery",
    environments={
        "celery": {
            "executor": "celery",
            "executor_config": {
                "broker_url": "redis://redis:6379/0",
                "result_backend": "redis://redis:6379/1",
                "task_name": "myapp.wove_task",
                "queue": "wove",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

You can also pass an existing Celery app as `executor_config["app"]`. If `app` is omitted, Wove creates one from `broker_url`, `result_backend`, and `app_name`.

## Worker Task

```python
from celery import Celery
from wove.integrations.worker import run

app = Celery("myapp", broker="redis://redis:6379/0", backend="redis://redis:6379/1")


@app.task(name="myapp.wove_task")
def wove_task(payload):
    return run(payload)
```

The worker must have Wove installed and must be able to import the application code referenced by the serialized task.

## Options

| Key | Effect |
| --- | --- |
| `app` | Existing Celery app. |
| `broker_url` | Broker URL used when Wove creates the app. |
| `result_backend` or `backend_url` | Result backend used when Wove creates the app. |
| `app_name` | App name used when Wove creates the app. Defaults to `wove`. |
| `task_name` | Celery task name to call. Defaults to `wove.run_backend_payload`. |
| `queue` | Optional Celery queue. |
| `send_task_options` | Extra keyword arguments passed to `app.send_task(...)`. |
| `terminate_on_cancel` | Passed to `revoke(..., terminate=...)` during cancellation. |

## Related Pages

- [Backend Adapters](index.md): callback flow and adapter responsibilities.
- [`wove.integrations`](../api/wove.integrations.md): worker entrypoints and adapter base class.

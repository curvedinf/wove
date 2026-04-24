# Taskiq

Taskiq is for async task queues where the worker task should stay explicit. Wove finds or receives a Taskiq task, calls `.kiq(payload)`, and waits for the worker to post the result frame back.

## Use When

- Your project already has a Taskiq broker.
- You want Wove to submit payloads to a named Taskiq task.
- Worker execution should be async.

## Execution Shape

1. Wove uses `task` directly or calls `broker.find_task(task_name)`.
2. Wove submits the payload with `.kiq(payload)`.
3. The Taskiq worker task calls `await wove.integrations.worker.arun(payload)`.
4. The worker posts Wove completion events back to the callback URL.

## Dependency

Install dispatch support and Taskiq in the submitting process and in Taskiq workers.

```bash
pip install "wove[dispatch]" taskiq
```

## Configure Wove

```python
import wove
from myapp.tasks import broker

wove.config(
    default_environment="taskiq",
    environments={
        "taskiq": {
            "executor": "taskiq",
            "executor_config": {
                "broker": broker,
                "task_name": "myapp.wove_task",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

You can pass a specific task as `executor_config["task"]`. If `task` is omitted, Wove calls `broker.find_task(task_name)`.

## Worker Task

```python
from taskiq import InMemoryBroker
from wove.integrations.worker import arun

broker = InMemoryBroker()


@broker.task(task_name="myapp.wove_task")
async def run_wove_payload(payload):
    return await arun(payload)
```

Use your production broker in real deployments; the in-memory broker is only for the compact example.

## Options

| Key | Effect |
| --- | --- |
| `task` | Explicit Taskiq task object. |
| `broker` | Broker used to find the task. |
| `task_name` | Task name passed to `broker.find_task(...)`. Defaults to `wove.run_backend_payload`. |

## Related Pages

- [Backend Adapters](index.md): callback flow and adapter responsibilities.
- [`wove.integrations`](../api/wove.integrations.md): worker entrypoints.

# Temporal

Temporal is for work that should enter an existing Temporal task queue while the weave keeps its inline dependency graph. Wove starts a workflow with the payload; the workflow should run an activity that executes the payload and posts the result back to Wove.

## Use When

- Your production work already belongs in Temporal.
- You need Temporal's workflow/task-queue deployment model.
- The Wove task should be executed inside a Temporal activity, not in the submitting process.

## Execution Shape

1. Wove calls `client.start_workflow(...)` with the payload.
2. The workflow receives the payload.
3. The workflow runs an activity that calls `await wove.integrations.worker.arun(payload)`.
4. The activity posts Wove event frames back to the callback URL.

## Dependency

```bash
pip install temporalio
```

## Configure Wove

```python
import wove
from myapp.temporal_worker import WovePayloadWorkflow

wove.config(
    default_environment="temporal",
    environments={
        "temporal": {
            "executor": "temporal",
            "executor_config": {
                "target_host": "temporal:7233",
                "workflow": WovePayloadWorkflow.run,
                "task_queue": "wove",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

You can pass an already connected Temporal client as `executor_config["client"]`. If `client` is omitted, Wove connects with `target_host` and `connect_options`.

## Worker Workflow

```python
from datetime import timedelta

from temporalio import activity, workflow
from wove.integrations.worker import arun


@activity.defn
async def run_wove_payload(payload):
    return await arun(payload)


@workflow.defn
class WovePayloadWorkflow:
    @workflow.run
    async def run(self, payload):
        return await workflow.execute_activity(
            run_wove_payload,
            payload,
            schedule_to_close_timeout=timedelta(minutes=30),
        )
```

Temporal workflows must remain deterministic. Keep Wove payload execution inside an activity.

## Options

| Key | Effect |
| --- | --- |
| `client` | Existing `temporalio.client.Client`. |
| `target_host` | Temporal server address used when Wove creates the client. |
| `connect_options` | Extra keyword arguments passed to `Client.connect(...)`. |
| `workflow` | Workflow function/name passed to `client.start_workflow(...)`. |
| `task_queue` | Temporal task queue. |
| `workflow_id_prefix` | Prefix for generated workflow IDs. Defaults to `wove`. |
| `start_options` | Extra keyword arguments passed to `client.start_workflow(...)`. |

## Related Pages

- [Executors](index.md): remote callback flow.
- [`wove.remote`](../api/wove.remote.md): callback transport.

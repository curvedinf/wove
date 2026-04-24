# AWS Batch

AWS Batch is for queueing Wove tasks onto managed Batch compute environments. Wove submits a Batch job, injects the payload into `WOVE_BACKEND_PAYLOAD`, and the container runs `python -m wove.backend_worker`.

## Use When

- Work should run on AWS Batch compute environments.
- Each task should be scheduled as a managed Batch job.
- The worker container can reach Wove's callback URL.

## Execution Shape

1. Wove calls `submit_job(...)` on a boto3 Batch client.
2. The job receives the payload as the `WOVE_BACKEND_PAYLOAD` environment variable.
3. The container runs `python -m wove.backend_worker`.
4. The worker posts Wove event frames back to the callback URL.

## Dependency

Install dispatch support and boto3 in the submitting process. The worker image must also include Wove with dispatch support.

```bash
pip install "wove[dispatch]" boto3
```

## Configure Wove

```python
import wove

wove.config(
    default_environment="aws_batch",
    environments={
        "aws_batch": {
            "executor": "aws_batch",
            "executor_config": {
                "job_queue": "wove",
                "job_definition": "wove-worker:1",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

The job definition should run Wove's dispatched worker, either as the image command or through `container_overrides`.

```bash
python -m wove.backend_worker
```

## Container Requirements

The container must have Wove and the application code installed, and it must be able to reach the callback URL.

## Options

| Key | Effect |
| --- | --- |
| `client` | Existing boto3 Batch client. |
| `client_options` | Keyword arguments passed to `boto3.client('batch', ...)`. |
| `job_queue` | AWS Batch job queue. |
| `job_definition` | AWS Batch job definition. |
| `container_overrides` | Base container overrides; Wove appends `WOVE_BACKEND_PAYLOAD`. |
| `command` | Optional command inserted into `containerOverrides`. |
| `submit_job_options` | Extra keyword arguments passed to `submit_job(...)`. |
| `job_name_prefix` | Generated job name prefix. Defaults to `wove`. |

## Related Pages

- [`wove.backend`](../api/wove.backend.md): backend payload worker behavior.
- [Backend Adapters](index.md): callback flow and adapter responsibilities.

# Kubernetes Jobs

Kubernetes Jobs are for isolated pod-per-task execution. Wove creates a Job, injects the payload into `WOVE_REMOTE_PAYLOAD`, and the container runs `python -m wove.remote_worker`.

## Use When

- Each task should run in a fresh pod.
- Work needs Kubernetes scheduling, image isolation, service accounts, or pod-level resource control.
- A long-lived queue worker is not the right deployment shape.

## Execution Shape

1. Wove builds a Kubernetes Job object.
2. The Job receives the payload as the `WOVE_REMOTE_PAYLOAD` environment variable.
3. The container runs `python -m wove.remote_worker`.
4. The worker posts Wove event frames back to the callback URL.

## Dependency

```bash
pip install kubernetes
```

## Configure Wove

```python
import wove

wove.config(
    default_environment="kubernetes_jobs",
    environments={
        "kubernetes_jobs": {
            "executor": "kubernetes_jobs",
            "executor_config": {
                "namespace": "jobs",
                "image": "registry.example.com/myapp-worker:latest",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

The image must contain Wove, your application code, and a Python runtime that can import the serialized task dependencies.

## Default Container Command

```bash
python -m wove.remote_worker
```

## Custom Job Shape

Use `job_factory` when the cluster needs custom labels, service accounts, resource limits, volumes, sidecars, or scheduling settings.

```python
def make_job(payload, frame, config):
    ...

wove.config(
    environments={
        "jobs": {
            "executor": "kubernetes_jobs",
            "executor_config": {
                "namespace": "jobs",
                "job_factory": make_job,
            },
        }
    },
)
```

## Options

| Key | Effect |
| --- | --- |
| `namespace` | Kubernetes namespace. Defaults to `default`. |
| `image` | Image used by the default Job factory. |
| `command` | Container command. Defaults to `['python', '-m', 'wove.remote_worker']`. |
| `job_factory` | Callable that returns a Kubernetes Job object. |
| `batch_api` | Existing `BatchV1Api` client. |
| `load_config` | Set to `False` if Kubernetes config is already loaded. |
| `in_cluster` | Use in-cluster config when loading Kubernetes config. |
| `load_config_options` | Options passed to the Kubernetes config loader. |
| `backoff_limit` | Default Job backoff limit. |
| `job_name_prefix` | Generated Job name prefix. Defaults to `wove`. |

## Related Pages

- [`wove.remote`](../api/wove.remote.md): `remote_worker` payload behavior.
- [Executors](index.md): remote callback flow.

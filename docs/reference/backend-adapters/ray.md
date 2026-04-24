# Ray

Ray is for sending Wove tasks into a Ray cluster without writing a separate backend-specific task wrapper. Wove wraps its worker entrypoint as a Ray remote function and submits the payload directly.

## Use When

- Your application already uses Ray for distributed Python execution.
- Wove tasks should run on Ray workers rather than the submitting process.
- The Ray workers can import Wove and your application code.

## Execution Shape

1. Wove initializes Ray unless `init=False`.
2. Wove wraps `wove.integrations.worker.run` with `ray.remote(...)`.
3. The remote function executes the payload.
4. The worker posts Wove event frames back to the callback URL.

## Dependency

Install dispatch support and Ray in the submitting process and on Ray workers that execute Wove payloads.

```bash
pip install "wove[dispatch]" ray
```

## Configure Wove

```python
import wove

wove.config(
    default_environment="ray",
    environments={
        "ray": {
            "executor": "ray",
            "executor_config": {
                "address": "ray://ray-head:10001",
                "remote_options": {"num_cpus": 1},
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

## Worker Requirements

Ray workers must have Wove installed and must be able to import the application code used by the serialized task.

## Options

| Key | Effect |
| --- | --- |
| `address` | Ray cluster address passed to `ray.init(...)`. |
| `init` | Set to `False` if the process already initialized Ray. |
| `init_options` | Extra keyword arguments passed to `ray.init(...)`. |
| `remote_options` | Options passed to `ray.remote(...)`. |
| `force_cancel` | Passed to `ray.cancel(..., force=...)`. |

## Related Pages

- [Backend Adapters](index.md): callback flow and adapter responsibilities.
- [`wove.integrations`](../api/wove.integrations.md): worker entrypoints.

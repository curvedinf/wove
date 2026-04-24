# Dask

Dask is for distributed Python execution through an existing Dask scheduler and worker pool. Wove submits its worker entrypoint to the Dask client and receives completion through the callback URL.

## Use When

- Your project already has a Dask distributed scheduler.
- Wove tasks should run on Dask workers.
- Workers can import Wove and application code.

## Execution Shape

1. Wove creates or uses a `distributed.Client`.
2. Wove submits `wove.integrations.worker.run(payload)` with `client.submit(...)`.
3. A Dask worker executes the payload.
4. The worker posts Wove completion events back to the callback URL.

## Dependency

Install dispatch support and Dask distributed in the submitting process and on Dask workers.

```bash
pip install "wove[dispatch]" "dask[distributed]"
```

## Configure Wove

```python
import wove

wove.config(
    default_environment="dask",
    environments={
        "dask": {
            "executor": "dask",
            "executor_config": {
                "address": "tcp://scheduler:8786",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

You can pass an existing client as `executor_config["client"]`. If `client` is omitted, Wove creates one from `address` and `client_options`.

## Worker Requirements

Dask workers must have Wove installed and must be able to import the application code used by the serialized task.

## Options

| Key | Effect |
| --- | --- |
| `client` | Existing `distributed.Client`. |
| `address` | Scheduler address used when Wove creates the client. |
| `client_options` | Extra keyword arguments passed to `Client(...)`. |
| `submit_options` | Extra keyword arguments passed to `client.submit(...)`. |

## Related Pages

- [Backend Adapters](index.md): callback flow and adapter responsibilities.
- [`wove.integrations`](../api/wove.integrations.md): worker entrypoints.

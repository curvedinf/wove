# Slurm

Slurm is for HPC environments where selected Wove tasks should run as scheduled batch jobs. The default path submits `sbatch --wrap` with `WOVE_BACKEND_PAYLOAD` and runs `python -m wove.backend_worker`.

## Use When

- Work should run through an existing Slurm scheduler.
- Tasks need cluster scheduling, accounting, partitions, or HPC resources.
- You can provide a worker environment with Wove and application code installed.

## Execution Shape

1. Wove submits a Slurm job with `sbatch` or a custom `submit` callable.
2. The job receives the payload as `WOVE_BACKEND_PAYLOAD`.
3. The job runs `python -m wove.backend_worker` or your configured command.
4. The worker posts Wove event frames back to the callback URL.

## Dependency

Install dispatch support and Slurm client bindings in the submitting process. The job environment must also include Wove with dispatch support.

```bash
pip install "wove[dispatch]" pyslurm
```

Wove checks for `pyslurm` so Slurm support fails clearly when the environment is not prepared. The default submission path uses `sbatch` and `scancel` because those commands are the most portable interface across clusters.

## Configure Wove

```python
import wove

wove.config(
    default_environment="slurm",
    environments={
        "slurm": {
            "executor": "slurm",
            "executor_config": {
                "command": "python -m wove.backend_worker",
                "callback_token": "shared-secret",
                "callback_url": "https://wove-runner.internal/wove/events/shared-secret",
            },
        }
    },
)
```

## Custom Submission

Use `submit` when the cluster needs project-specific `sbatch` options, modules, containers, partitions, or accounting flags.

```python
async def submit_to_slurm(payload, frame, config):
    ...

wove.config(
    environments={
        "slurm": {
            "executor": "slurm",
            "executor_config": {"submit": submit_to_slurm},
        }
    },
)
```

## Options

| Key | Effect |
| --- | --- |
| `submit` | Custom callable that receives `(payload, frame, config)`. |
| `command` | Command run by the default `sbatch --wrap` path. Defaults to `python -m wove.backend_worker`. |
| `sbatch` | Base command list for submission. Defaults to `['sbatch', '--parsable']`. |
| `scancel` | Base command list for cancellation. Defaults to `['scancel']`. |
| `job_name_prefix` | Generated job name prefix. Defaults to `wove`. |

## Related Pages

- [`wove.backend`](../api/wove.backend.md): backend payload worker behavior.
- [Backend Adapters](index.md): callback flow and adapter responsibilities.

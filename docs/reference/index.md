# Reference

Reference is for exact behavior: public imports, configuration shape, environment resolution, executor contracts, and backend adapter setup. Use the topic guides when learning Wove for the first time; use this section when you need to check names, options, frame shapes, or integration requirements.

## Start Here

- [Public API](api/wove.md): the import surface most users should rely on.
- [Environments](environments/index.md): how persistent execution profiles are defined and resolved.
- [Executors](executors/index.md): the contract every local, subprocess, or remote backend uses.
- [Executor Errors](executors/executor-errors.md): normalized task errors, delivery timeouts, and cancellation behavior.

## Public API

These pages document the Python modules that users and extension authors are expected to touch.

- [`wove`](api/wove.md): package entrypoints including `weave`, `Weave`, `config`, helpers, and exported exceptions.
- [`wove.weave`](api/wove.weave.md): reusable workflow classes and inheritable weave definitions.
- [`wove.helpers`](api/wove.helpers.md): data-shaping helpers used inside task graphs.
- [`wove.context`](api/wove.context.md): context manager implementation behind `with weave() as w:`.

## Configuration And Runtime

These pages describe how Wove decides where work runs and how runtime defaults are applied.

- [`wove.runtime`](api/wove.runtime.md): process-wide configuration singleton and `wove.config(...)` behavior.
- [Environments](environments/index.md): environment dictionaries, precedence, defaults, and validation rules.
- [`wove.environment`](api/wove.environment.md): executor interfaces, runtime delivery errors, and executor runtime classes.

## Remote Execution Internals

These pages are for users wiring Wove into task infrastructure or implementing their own adapter.

- [Executors](executors/index.md): frame protocol, executor lifecycle, and remote callback flow.
- [`wove.remote`](api/wove.remote.md): callback receiver, payload serialization, and remote worker helpers.
- [`wove.integrations`](api/wove.integrations.md): adapter registry, adapter base interface, and worker entrypoints.

## Backend Adapters

Each adapter page explains what Wove submits, what the worker must run, and which `executor_config` keys matter.

- [Celery](executors/celery.md): broker-backed worker pools.
- [Temporal](executors/temporal.md): workflow/task-queue execution.
- [Ray](executors/ray.md): Ray cluster tasks.
- [RQ](executors/rq.md): Redis Queue workers.
- [Taskiq](executors/taskiq.md): async task queues with explicit task registration.
- [ARQ](executors/arq.md): async Redis worker functions.
- [Dask](executors/dask.md): distributed Python scheduler workers.
- [Kubernetes Jobs](executors/kubernetes-jobs.md): isolated pod-per-task execution.
- [AWS Batch](executors/aws-batch.md): managed batch compute jobs.
- [Slurm](executors/slurm.md): HPC batch scheduling.

```{toctree}
:maxdepth: 2
:hidden:

api/wove
api/wove.context
api/wove.weave
api/wove.runtime
api/wove.environment
api/wove.remote
api/wove.integrations
api/wove.helpers
environments/index
executors/index
```

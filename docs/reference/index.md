# Reference

Reference material is for exact behavior after the shape of a weave is already clear: public imports, configuration keys, environment resolution, executor frames, and backend adapter requirements. The topic guides explain the workflow model; the reference pages pin down names, options, and runtime contracts.

## Core References

- [Public API](api/wove.md): the import surface most users should rely on.
- [Environments](environments/index.md): how persistent execution profiles are defined and resolved.
- [Executors](executors/index.md): executor contracts, error frames, dispatch extras, network executors, and custom executor extension points.
- [Backend Adapters](backend-adapters/index.md): setup for Wove's built-in bridges into external task systems and custom backend adapter extension points.

## Public API

The public API references separate the stable import surface from modules that mainly matter when inspecting internals.

- [`wove`](api/wove.md): package entrypoints including `weave`, `Weave`, `config`, helpers, and exported exceptions.
- [`wove.weave`](api/wove.weave.md): reusable workflow classes and inheritable weave definitions.
- [`wove.helpers`](api/wove.helpers.md): data-shaping helpers used inside task graphs.
- [`wove.context`](api/wove.context.md): context manager implementation behind `with weave() as w:`.

## Configuration And Runtime

Runtime references trace how Wove resolves project defaults, named environments, task-level overrides, and executor instances when work is not running where expected.

- [`wove.runtime`](api/wove.runtime.md): process-wide configuration singleton and `wove.config(...)` behavior.
- [Environments](environments/index.md): environment dictionaries, precedence, defaults, and validation rules.
- [`wove.environment`](api/wove.environment.md): executor interfaces, runtime delivery errors, and executor runtime classes.
- [`wove.security`](api/wove.security.md): network executor request signing and verification helpers.

## Dispatch And Remote Execution

Remote execution references separate the direct executor protocol, worker-service flow, backend callback flow, and adapter contract so the two extension shapes do not blur together.

- [Executors](executors/index.md): frame protocol, executor lifecycle, and network executors.
- [HTTP/HTTPS Executor](executors/http-executor.md): direct request/response transport for worker services.
- [gRPC Executor](executors/grpc-executor.md): generic unary RPC transport for gRPC-based worker services.
- [WebSocket Executor](executors/websocket-executor.md): persistent bidirectional transport for worker services that stream events.
- [Custom Executors](executors/custom-executors.md): direct executor implementations for project-owned transports or runtimes.
- [Backend Adapters](backend-adapters/index.md): built-in bridges into Celery, Temporal, Ray, Kubernetes, AWS Batch, Slurm, and similar systems.
- [Custom Backend Adapters](backend-adapters/custom-backend-adapters.md): adapter implementations for project-owned task systems.
- [`wove.backend`](api/wove.backend.md): backend callback transport and dispatch payload helpers.
- [`wove.integrations`](api/wove.integrations.md): adapter registry, adapter base interface, and worker entrypoints.
- [`wove.security`](api/wove.security.md): shared security layer for HTTP, gRPC, and WebSocket network executors.

## Backend Adapters

Each adapter page shows what Wove submits to that system, what the worker must run, and which `executor_config` keys matter.

- [Celery](backend-adapters/celery.md): broker-backed worker pools.
- [Temporal](backend-adapters/temporal.md): workflow/task-queue execution.
- [Ray](backend-adapters/ray.md): Ray cluster tasks.
- [RQ](backend-adapters/rq.md): Redis Queue workers.
- [Taskiq](backend-adapters/taskiq.md): async task queues with explicit task registration.
- [ARQ](backend-adapters/arq.md): async Redis worker functions.
- [Dask](backend-adapters/dask.md): distributed Python scheduler workers.
- [Kubernetes Jobs](backend-adapters/kubernetes-jobs.md): isolated pod-per-task execution.
- [AWS Batch](backend-adapters/aws-batch.md): managed batch compute jobs.
- [Slurm](backend-adapters/slurm.md): HPC batch scheduling.
- [Custom Backend Adapters](backend-adapters/custom-backend-adapters.md): project-local bridges into systems Wove does not ship with.

```{toctree}
:maxdepth: 2
:hidden:

api/wove
api/wove.context
api/wove.weave
api/wove.runtime
api/wove.environment
api/wove.security
api/wove.backend
api/wove.integrations
api/wove.helpers
environments/index
executors/index
backend-adapters/index
```

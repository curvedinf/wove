# [![Wove](_static/wove.svg)](index.md)

Beautiful Python async.

## What is Wove For?

Wove is for running high latency async tasks like web requests and database queries concurrently in the same way as
asyncio, but with a drastically improved user experience.

Improvements compared to asyncio include:

- **Reads Top-to-Bottom**: The workflow is declared in the order it runs, inline with the code that needs the result.
- **Implicit Parallelism**: Parallelism and execution order are implicit based on function and parameter naming.
- **Sync or Async**: Mix `async def` and `def` freely without restructuring the call site around one concurrency style.
- **Normal Python Data**: Task outputs behave like normal Python values without making you manage shared mutable state.
- **Automatic Scheduling**: Wove builds a dependency graph from your task signatures and runs independent tasks concurrently as soon as possible.
- **Automatic Detachment**: Run inline workflows outside the current request, command, or worker when waiting would be the wrong user experience.
- **Remote Task Environments**: Keep quick work local while sending selected long-running or infrastructure-heavy tasks to your worker service, queue, workflow engine, cluster, or scheduler.
- **Extensibility**: Define parallelized workflow templates that can be overridden inline.
- **High Visibility**: Wove includes debugging tools that allow you to identify where exceptions and deadlocks occur across parallel tasks, and inspect inputs and outputs at each stage of execution.
- **Minimal Boilerplate**: Get started with just the `with weave() as w:` context manager and the `@w.do` decorator.
- **Fast**: Wove has low overhead and internally uses `asyncio`, so performance is comparable to using `threading` or `asyncio` directly.
- **Free Threading Compatible**: Running a modern GIL-less Python? Build true multithreading without changing the workflow shape.
- **Zero Required Dispatch/Backend Dependencies**: Local Wove stays lightweight. Extra serialization and backend libraries are only needed when work leaves the current process.

## Topics

- [The Basics](how-to/the-basics.md)
- [Task Mapping](how-to/task-mapping.md)
- [Inheritable Weaves](how-to/inheritable-weaves.md)
- [Merging External Functions](how-to/merging-external-functions.md)
- [Helper Functions](how-to/helper-functions.md)
- [Error Handling](how-to/error-handling.md)
- [Debugging & Introspection](how-to/debugging-introspection.md)
- [Background Processing](how-to/background-processing.md)
- [Remote Task Environments](how-to/remote-task-environments.md)
- [Patterns For Production](how-to/patterns-for-production.md)

## Reference

When you already know the workflow you want and need exact behavior, start here. Wove's reference material pins down public imports, configuration shape, environment resolution, executor contracts, network executors, and backend adapter setup.

### Core Behavior

Start with the core behavior references when you need to confirm which names are public, how Wove resolves execution settings, and what guarantees the runtime makes before you tune or extend it.

- [Public API](reference/api/wove.md): stable imports most users should rely on.
- [Environments](reference/environments/index.md): persistent execution profiles, defaults, and precedence rules.
- [Executors](reference/executors/index.md)
- [Backend Adapters](reference/backend-adapters/index.md)

### Runtime Modules

If you are tracing a public concept back to its implementation module, the runtime module references connect the friendly API to the objects that enforce it.

- [`wove.runtime`](reference/api/wove.runtime.md): process-wide `wove.config(...)` behavior.
- [`wove.environment`](reference/api/wove.environment.md): executor interfaces, runtime delivery errors, and executor runtime classes.
- [`wove.backend`](reference/api/wove.backend.md): backend callback transport and dispatch payload helpers.
- [`wove.integrations`](reference/api/wove.integrations.md): adapter registry, adapter base interface, and worker entrypoints.

### Executors

Executors define how a Wove environment delivers task frames. Use these pages when the task should run locally, through a subprocess, or through a direct worker service over HTTP, gRPC, or WebSocket.

- [Executors](reference/executors/index.md)
  - [Local Executor](reference/executors/local-executor.md)
  - [Stdio Executor](reference/executors/stdio-executor.md)
  - [HTTP/HTTPS Executor](reference/executors/http-executor.md)
  - [gRPC Executor](reference/executors/grpc-executor.md)
  - [WebSocket Executor](reference/executors/websocket-executor.md)
  - [Custom Executors](reference/executors/custom-executors.md)

### Backend Adapters

Backend adapters are separate from direct executors because the existing backend owns delivery behavior: queueing, scheduling, retries, worker placement, or batch execution. Use these pages when a Wove task should enter infrastructure your project already runs.

- [Backend Adapters](reference/backend-adapters/index.md)
  - [Celery](reference/backend-adapters/celery.md)
  - [Temporal](reference/backend-adapters/temporal.md)
  - [Ray](reference/backend-adapters/ray.md)
  - [RQ](reference/backend-adapters/rq.md)
  - [Taskiq](reference/backend-adapters/taskiq.md)
  - [ARQ](reference/backend-adapters/arq.md)
  - [Dask](reference/backend-adapters/dask.md)
  - [Kubernetes Jobs](reference/backend-adapters/kubernetes-jobs.md)
  - [AWS Batch](reference/backend-adapters/aws-batch.md)
  - [Slurm](reference/backend-adapters/slurm.md)
  - [Custom Backend Adapters](reference/backend-adapters/custom-backend-adapters.md)

## Version History

Wove's version history records the major and minor release series. Patch releases are not listed separately unless they change the shape of a series.

- [2.0.0](version-history/2.0.0.md): remote task environments and the new execution-environment layer.
- [1.0.0](version-history/1.0.0.md): stable local inline concurrency and background processing.
- [0.3.0](version-history/0.3.0.md): reusable weave classes, richer task controls, and helpers.
- [0.2.0](version-history/0.2.0.md): dynamic task mapping and executor management.
- [0.1.0](version-history/0.1.0.md): initial public release.

```{toctree}
:hidden:
:maxdepth: 2

how-to/index
reference/index
```

```{toctree}
:hidden:
:maxdepth: 1
:caption: Version History

version-history/2.0.0
version-history/1.0.0
version-history/0.3.0
version-history/0.2.0
version-history/0.1.0
```

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
- **Zero Required Dependencies**: Core Wove installs without third-party packages. Serialization, networking, and backend libraries are only needed when a workflow opts into features that use them.

## Topics

The topic path starts with the smallest useful weave, then adds the things real workflows need as they grow: fanout, task policy, reuse, helper glue, failure handling, observability, background work, remote execution, and production patterns.

- [The Basics](how-to/the-basics.md): the core `weave()` and `@w.do` workflow.
- [Task Mapping](how-to/task-mapping.md): running one task or helper callable across many inputs and collecting the results.
- [Task Quality of Life](how-to/task-quality-of-life.md): task options that replace retry, timeout, fanout, and routing boilerplate.
- [Inheritable Weaves](how-to/inheritable-weaves.md): reusable workflow templates with inline overrides.
- [Helper Functions](how-to/helper-functions.md): small data-shaping tools that keep task glue readable.
- [Error Handling](how-to/error-handling.md): how task, background, and remote delivery failures surface.
- [Debugging & Introspection](how-to/debugging-introspection.md): graph, timing, mapping, and failure inspection.
- [Background Processing](how-to/background-processing.md): running a whole weave after the caller continues.
- [Remote Task Environments](how-to/remote-task-environments.md): sending selected tasks to other processes, services, queues, clusters, or schedulers.
- [Patterns For Production](how-to/patterns-for-production.md): common production workflow shapes built from Wove's core task, mapping, policy, background, and remote-execution building blocks.

## Reference

Reference material pins down the public surface of Wove: imports, configuration shape, environment resolution, executor contracts, network executors, and backend adapter setup. Reference pages answer what each feature accepts, returns, guarantees, and raises once the workflow shape is already clear.

### Core Behavior

Core behavior covers the names and runtime rules that everything else builds on: stable imports, environment resolution, and the guarantees Wove keeps before any executor-specific or adapter-specific behavior is involved.

- [Public API](reference/api/wove.md): stable imports most users should rely on.
- [Environments](reference/environments/index.md): persistent execution profiles, defaults, and precedence rules.
- [Executors](reference/executors/index.md): delivery interfaces for local, subprocess, and direct network execution.
- [Backend Adapters](reference/backend-adapters/index.md): bridges from Wove tasks into existing task systems, queues, clusters, and schedulers.

### Runtime Modules

Runtime module references connect public concepts back to the objects that implement and enforce them.

- [`wove.runtime`](reference/api/wove.runtime.md): process-wide `wove.config(...)` behavior.
- [`wove.environment`](reference/api/wove.environment.md): executor interfaces, runtime delivery errors, and executor runtime classes.
- [`wove.backend`](reference/api/wove.backend.md): backend callback transport and dispatch payload helpers.
- [`wove.integrations`](reference/api/wove.integrations.md): adapter registry, adapter base interface, and worker entrypoints.

### Executors

Executors are the delivery layer for Wove environments. They carry task frames to local execution, subprocess workers, or direct worker services over HTTP, gRPC, and WebSocket while keeping result collection attached to the weave.

- [Executors](reference/executors/index.md)
  - [Local Executor](reference/executors/local-executor.md)
  - [Stdio Executor](reference/executors/stdio-executor.md)
  - [HTTP/HTTPS Executor](reference/executors/http-executor.md)
  - [gRPC Executor](reference/executors/grpc-executor.md)
  - [WebSocket Executor](reference/executors/websocket-executor.md)
  - [Custom Executors](reference/executors/custom-executors.md)

### Backend Adapters

Backend adapters are separate from direct executors because an existing task system owns delivery behavior: queueing, scheduling, retries, worker placement, or batch execution. They let a Wove task enter infrastructure the project already runs while Wove keeps the task result attached to the local weave.

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

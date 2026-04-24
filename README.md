# ![Wove](wove.png)

[![PyPI](https://img.shields.io/pypi/v/wove)](https://pypi.org/project/wove/)
[![GitHub license](https://img.shields.io/github/license/curvedinf/wove)](LICENSE)
[![coverage](coverage.svg)](https://github.com/curvedinf/wove/actions/workflows/coverage.yml)
[![GitHub last commit](https://img.shields.io/github/last-commit/curvedinf/wove)](https://github.com/curvedinf/wove/commits/main)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/wove)](https://pypi.org/project/wove/)
[![GitHub stars](https://img.shields.io/github/stars/curvedinf/wove)](https://github.com/curvedinf/wove/stargazers)
[![Ko-fi Link](kofi.webp)](https://ko-fi.com/A0A31B6VB6)

[![Python 3.8](https://github.com/curvedinf/wove/actions/workflows/python-3-8.yml/badge.svg)](https://github.com/curvedinf/wove/actions/workflows/python-3-8.yml)
[![Python 3.9](https://github.com/curvedinf/wove/actions/workflows/python-3-9.yml/badge.svg)](https://github.com/curvedinf/wove/actions/workflows/python-3-9.yml)
[![Python 3.10](https://github.com/curvedinf/wove/actions/workflows/python-3-10.yml/badge.svg)](https://github.com/curvedinf/wove/actions/workflows/python-3-10.yml)
[![Python 3.11](https://github.com/curvedinf/wove/actions/workflows/python-3-11.yml/badge.svg)](https://github.com/curvedinf/wove/actions/workflows/python-3-11.yml)
[![Python 3.12](https://github.com/curvedinf/wove/actions/workflows/python-3-12.yml/badge.svg)](https://github.com/curvedinf/wove/actions/workflows/python-3-12.yml)
[![Python 3.13](https://github.com/curvedinf/wove/actions/workflows/python-3-13.yml/badge.svg)](https://github.com/curvedinf/wove/actions/workflows/python-3-13.yml)
[![Python 3.14](https://github.com/curvedinf/wove/actions/workflows/python-3-14.yml/badge.svg)](https://github.com/curvedinf/wove/actions/workflows/python-3-14.yml)
[![Python 3.14 (free-threaded)](https://github.com/curvedinf/wove/actions/workflows/python-3-14t.yml/badge.svg)](https://github.com/curvedinf/wove/actions/workflows/python-3-14t.yml)

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

The topic path starts with the smallest useful weave, then adds the things real workflows need as they grow: fanout, task policy, reuse, helper glue, failure handling, observability, background work, remote execution, and production patterns.

- [The Basics](docs/how-to/the-basics.md): the core `weave()` and `@w.do` workflow.
- [Task Mapping](docs/how-to/task-mapping.md): running one task across many inputs and collecting the results.
- [Task Quality of Life](docs/how-to/task-quality-of-life.md): task options that replace retry, timeout, fanout, and routing boilerplate.
- [Inheritable Weaves](docs/how-to/inheritable-weaves.md): reusable workflow templates with inline overrides.
- [Merging External Functions](docs/how-to/merging-external-functions.md): mapping helper callables without turning them into named tasks.
- [Helper Functions](docs/how-to/helper-functions.md): small data-shaping tools that keep task glue readable.
- [Error Handling](docs/how-to/error-handling.md): how task, background, and remote delivery failures surface.
- [Debugging & Introspection](docs/how-to/debugging-introspection.md): graph, timing, mapping, and failure inspection.
- [Background Processing](docs/how-to/background-processing.md): running a whole weave after the caller continues.
- [Remote Task Environments](docs/how-to/remote-task-environments.md): sending selected tasks to other processes, services, queues, clusters, or schedulers.
- [Patterns For Production](docs/how-to/patterns-for-production.md): common production workflow shapes built from Wove's core task, mapping, policy, background, and remote-execution building blocks.

## Reference

When you already know the workflow you want and need exact behavior, start here. Wove's reference material pins down public imports, configuration shape, environment resolution, executor contracts, network executors, and backend adapter setup.

### Core Behavior

Start with the core behavior references when you need to confirm which names are public, how Wove resolves execution settings, and what guarantees the runtime makes before you tune or extend it.

- [Public API](docs/reference/api/wove.md): stable imports most users should rely on.
- [Environments](docs/reference/environments/index.md): persistent execution profiles, defaults, and precedence rules.
- [Executors](docs/reference/executors/index.md)
- [Backend Adapters](docs/reference/backend-adapters/index.md)

### Runtime Modules

If you are tracing a public concept back to its implementation module, the runtime module references connect the friendly API to the objects that enforce it.

- [`wove.runtime`](docs/reference/api/wove.runtime.md): process-wide `wove.config(...)` behavior.
- [`wove.environment`](docs/reference/api/wove.environment.md): executor interfaces, runtime delivery errors, and executor runtime classes.
- [`wove.backend`](docs/reference/api/wove.backend.md): backend callback transport and dispatch payload helpers.
- [`wove.integrations`](docs/reference/api/wove.integrations.md): adapter registry, adapter base interface, and worker entrypoints.

### Executors

Executors define how a Wove environment delivers task frames. Use these pages when the task should run locally, through a subprocess, or through a direct worker service over HTTP, gRPC, or WebSocket.

- [Executors](docs/reference/executors/index.md)
  - [Local Executor](docs/reference/executors/local-executor.md)
  - [Stdio Executor](docs/reference/executors/stdio-executor.md)
  - [HTTP/HTTPS Executor](docs/reference/executors/http-executor.md)
  - [gRPC Executor](docs/reference/executors/grpc-executor.md)
  - [WebSocket Executor](docs/reference/executors/websocket-executor.md)
  - [Custom Executors](docs/reference/executors/custom-executors.md)

### Backend Adapters

Backend adapters are separate from direct executors because the existing backend owns delivery behavior: queueing, scheduling, retries, worker placement, or batch execution. Use these pages when a Wove task should enter infrastructure your project already runs.

- [Backend Adapters](docs/reference/backend-adapters/index.md)
  - [Celery](docs/reference/backend-adapters/celery.md)
  - [Temporal](docs/reference/backend-adapters/temporal.md)
  - [Ray](docs/reference/backend-adapters/ray.md)
  - [RQ](docs/reference/backend-adapters/rq.md)
  - [Taskiq](docs/reference/backend-adapters/taskiq.md)
  - [ARQ](docs/reference/backend-adapters/arq.md)
  - [Dask](docs/reference/backend-adapters/dask.md)
  - [Kubernetes Jobs](docs/reference/backend-adapters/kubernetes-jobs.md)
  - [AWS Batch](docs/reference/backend-adapters/aws-batch.md)
  - [Slurm](docs/reference/backend-adapters/slurm.md)
  - [Custom Backend Adapters](docs/reference/backend-adapters/custom-backend-adapters.md)

## Version History

Wove's version history records the major and minor release series. Patch releases are not listed separately unless they change the shape of a series.

- [2.0.0](docs/version-history/2.0.0.md): remote task environments and the new execution-environment layer.
- [1.0.0](docs/version-history/1.0.0.md): stable local inline concurrency and background processing.
- [0.3.0](docs/version-history/0.3.0.md): reusable weave classes, richer task controls, and helpers.
- [0.2.0](docs/version-history/0.2.0.md): dynamic task mapping and executor management.
- [0.1.0](docs/version-history/0.1.0.md): initial public release.

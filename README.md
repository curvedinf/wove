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

## Documentation

The full documentation includes topic guides, API reference pages, executor setup, backend adapter setup, and version history.

[View Documentation](https://curvedinf.github.io/wove/)

## Topics

The topic path starts with the smallest useful weave, then adds the things real workflows need as they grow: fanout, task policy, reuse, helper glue, failure handling, observability, background work, remote execution, and production patterns.

- [The Basics](https://curvedinf.github.io/wove/how-to/the-basics.html): the core `weave()` and `@w.do` workflow.
- [Task Mapping](https://curvedinf.github.io/wove/how-to/task-mapping.html): running one task or helper callable across many inputs and collecting the results.
- [Task Quality of Life](https://curvedinf.github.io/wove/how-to/task-quality-of-life.html): task options that replace retry, timeout, fanout, and routing boilerplate.
- [Inheritable Weaves](https://curvedinf.github.io/wove/how-to/inheritable-weaves.html): reusable workflow templates with inline overrides.
- [Helper Functions](https://curvedinf.github.io/wove/how-to/helper-functions.html): small data-shaping tools that keep task glue readable.
- [Error Handling](https://curvedinf.github.io/wove/how-to/error-handling.html): how task, background, and remote delivery failures surface.
- [Debugging & Introspection](https://curvedinf.github.io/wove/how-to/debugging-introspection.html): graph, timing, mapping, and failure inspection.
- [Background Processing](https://curvedinf.github.io/wove/how-to/background-processing.html): running a whole weave after the caller continues.
- [Remote Task Environments](https://curvedinf.github.io/wove/how-to/remote-task-environments.html): sending selected tasks to other processes, services, queues, clusters, or schedulers.
- [Patterns For Production](https://curvedinf.github.io/wove/how-to/patterns-for-production.html): common production workflow shapes built from Wove's core task, mapping, policy, background, and remote-execution building blocks.

## Reference

Reference material pins down the public surface of Wove: imports, configuration shape, environment resolution, executor contracts, network executors, and backend adapter setup. It is the part of the documentation that answers what each feature accepts, returns, guarantees, and raises once the workflow shape is already clear.

### Core Behavior

Core behavior covers the names and runtime rules that everything else builds on: stable imports, environment resolution, and the guarantees Wove keeps before any executor-specific or adapter-specific behavior is involved.

- [Public API](https://curvedinf.github.io/wove/reference/api/wove.html): stable imports most users should rely on.
- [Environments](https://curvedinf.github.io/wove/reference/environments/): persistent execution profiles, defaults, and precedence rules.
- [Executors](https://curvedinf.github.io/wove/reference/executors/): delivery interfaces for local, subprocess, and direct network execution.
- [Backend Adapters](https://curvedinf.github.io/wove/reference/backend-adapters/): bridges from Wove tasks into existing task systems, queues, clusters, and schedulers.

### Runtime Modules

If you are tracing a public concept back to its implementation module, the runtime module references connect the friendly API to the objects that enforce it.

- [`wove.runtime`](https://curvedinf.github.io/wove/reference/api/wove.runtime.html): process-wide `wove.config(...)` behavior.
- [`wove.environment`](https://curvedinf.github.io/wove/reference/api/wove.environment.html): executor interfaces, runtime delivery errors, and executor runtime classes.
- [`wove.backend`](https://curvedinf.github.io/wove/reference/api/wove.backend.html): backend callback transport and dispatch payload helpers.
- [`wove.integrations`](https://curvedinf.github.io/wove/reference/api/wove.integrations.html): adapter registry, adapter base interface, and worker entrypoints.

### Executors

Executors are the delivery layer for Wove environments. They carry task frames to local execution, subprocess workers, or direct worker services over HTTP, gRPC, and WebSocket while keeping result collection attached to the weave.

- [Executors](https://curvedinf.github.io/wove/reference/executors/)
  - [Local Executor](https://curvedinf.github.io/wove/reference/executors/local-executor.html)
  - [Stdio Executor](https://curvedinf.github.io/wove/reference/executors/stdio-executor.html)
  - [HTTP/HTTPS Executor](https://curvedinf.github.io/wove/reference/executors/http-executor.html)
  - [gRPC Executor](https://curvedinf.github.io/wove/reference/executors/grpc-executor.html)
  - [WebSocket Executor](https://curvedinf.github.io/wove/reference/executors/websocket-executor.html)
  - [Custom Executors](https://curvedinf.github.io/wove/reference/executors/custom-executors.html)

### Backend Adapters

Backend adapters are separate from direct executors because an existing task system owns delivery behavior: queueing, scheduling, retries, worker placement, or batch execution. They let a Wove task enter infrastructure the project already runs while Wove keeps the task result attached to the local weave.

- [Backend Adapters](https://curvedinf.github.io/wove/reference/backend-adapters/)
  - [Celery](https://curvedinf.github.io/wove/reference/backend-adapters/celery.html)
  - [Temporal](https://curvedinf.github.io/wove/reference/backend-adapters/temporal.html)
  - [Ray](https://curvedinf.github.io/wove/reference/backend-adapters/ray.html)
  - [RQ](https://curvedinf.github.io/wove/reference/backend-adapters/rq.html)
  - [Taskiq](https://curvedinf.github.io/wove/reference/backend-adapters/taskiq.html)
  - [ARQ](https://curvedinf.github.io/wove/reference/backend-adapters/arq.html)
  - [Dask](https://curvedinf.github.io/wove/reference/backend-adapters/dask.html)
  - [Kubernetes Jobs](https://curvedinf.github.io/wove/reference/backend-adapters/kubernetes-jobs.html)
  - [AWS Batch](https://curvedinf.github.io/wove/reference/backend-adapters/aws-batch.html)
  - [Slurm](https://curvedinf.github.io/wove/reference/backend-adapters/slurm.html)
  - [Custom Backend Adapters](https://curvedinf.github.io/wove/reference/backend-adapters/custom-backend-adapters.html)

## Version History

Wove's version history records the major and minor release series. Patch releases are not listed separately unless they change the shape of a series.

- [2.0.0](https://curvedinf.github.io/wove/version-history/2.0.0.html): remote task environments and the new execution-environment layer.
- [1.0.0](https://curvedinf.github.io/wove/version-history/1.0.0.html): stable local inline concurrency and background processing.
- [0.3.0](https://curvedinf.github.io/wove/version-history/0.3.0.html): reusable weave classes, richer task controls, and helpers.
- [0.2.0](https://curvedinf.github.io/wove/version-history/0.2.0.html): dynamic task mapping and executor management.
- [0.1.0](https://curvedinf.github.io/wove/version-history/0.1.0.html): initial public release.

## Benchmarks

Wove has low overhead and internally uses `asyncio`, so its performance is comparable to using `threading` or `asyncio` directly. The benchmark script below is available in the `/examples` directory.

```bash
$ python examples/benchmark.py
Starting performance benchmarks...
Number of tasks: 200
CPU load iterations per task: 100000
I/O sleep duration per task: 0.1s
===================================
--- Running Threading Benchmark ---
Threading total time: 0.6978 seconds
-----------------------------------
--- Running Asyncio Benchmark ---
Asyncio total time: 0.6831 seconds
-----------------------------------
--- Running Wove Benchmark ---
Wove timing details:
  - data: 0.5908s
  - planning: 0.0001s
  - tier_1_execution: 0.6902s
  - tier_1_post_execution: 0.0000s
  - tier_1_pre_execution: 0.0004s
  - wove_task: 0.6882s
Wove total time: 0.6937 seconds
-----------------------------------
--- Running Wove Async Benchmark ---
Wove Async timing details:
  - data: 0.5515s
  - planning: 0.0000s
  - tier_1_execution: 0.6550s
  - tier_1_post_execution: 0.0000s
  - tier_1_pre_execution: 0.0004s
  - wove_async_task: 0.6534s
Wove Async total time: 0.6571 seconds
-----------------------------------
Benchmarks finished.
```

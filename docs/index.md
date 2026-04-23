# [![Wove](_static/wove.svg)](index.md)

Beautiful Python async.

## What is Wove For?

Wove is for running high latency async tasks like web requests and database queries concurrently in the same way as
asyncio, but with a drastically improved user experience.

Improvements compared to asyncio include:

- **Reads Top-to-Bottom**: The code in a `weave` block is declared in the order it is executed inline in your code instead of in disjointed functions.
- **Implicit Parallelism**: Parallelism and execution order are implicit based on function and parameter naming.
- **Sync or Async**: Mix `async def` and `def` freely. A `weave` block can be inside or outside an async context. Sync functions are run in a background thread pool to avoid blocking the event loop.
- **Normal Python Data**: Wove's task data looks like normal Python variables because it is. This is because of inherent multithreaded data safety produced in the same way as map-reduce.
- **Automatic Scheduling**: Wove builds a dependency graph from your task signatures and runs independent tasks concurrently as soon as possible.
- **Automatic Detachment**: Wove can run your inline code in a forked detached process so you can return your current process back to your server's pool.
- **Remote Execution Environments**: Route selected tasks to existing task systems like Celery, Temporal, Ray, RQ, Taskiq, ARQ, Dask, Kubernetes Jobs, AWS Batch, or Slurm while keeping the weave inline and task code unchanged.
- **Extensibility**: Define parallelized workflow templates that can be overridden inline.
- **High Visibility**: Wove includes debugging tools that allow you to identify where exceptions and deadlocks occur across parallel tasks, and inspect inputs and outputs at each stage of execution.
- **Minimal Boilerplate**: Get started with just the `with weave() as w:` context manager and the `@w.do` decorator.
- **Fast**: Wove has low overhead and internally uses `asyncio`, so performance is comparable to using `threading` or `asyncio` directly.
- **Free Threading Compatible**: Running a modern GIL-less Python? Build true multithreading easily with a `weave`.
- **Zero Required Backend Dependencies**: Wove's core is pure Python with optional integrations for remote task systems. It can be easily integrated into any Python project whether the project uses `asyncio` or not.

## Topics

- [The Basics](how-to/the-basics.md)
- [Local Task Mapping](how-to/local-task-mapping.md)
- [Dependent Task Mapping](how-to/dependent-task-mapping.md)
- [Inheritable Weaves](how-to/inheritable-weaves.md)
- [Merging External Functions](how-to/merging-external-functions.md)
- [Error Handling](how-to/error-handling.md)
- [Debugging & Introspection](how-to/debugging-introspection.md)
- [Background Processing](how-to/background-processing.md)
- [Advanced/Remote Execution Environments](how-to/advanced-remote-execution-environments.md)

## Reference

Reference is for exact behavior: public imports, configuration shape, environment resolution, executor contracts, and backend adapter setup.

### Core Behavior

These are the reference pages most readers need when they want to check the shape and guarantees of Wove itself.

- [Public API](reference/api/wove.md): stable imports most users should rely on.
- [Environments](reference/environments/index.md): persistent execution profiles, defaults, and precedence rules.
- [Executors](reference/executors/index.md): executor choices, frame contracts, and remote callback flow.
- [Executor Errors](reference/executors/executor-errors.md): normalized task errors, delivery timeouts, and cancellation behavior.

### Runtime Modules

These pages map the public concepts back to the modules that implement them.

- [`wove.runtime`](reference/api/wove.runtime.md): process-wide `wove.config(...)` behavior.
- [`wove.environment`](reference/api/wove.environment.md): executor interfaces, runtime delivery errors, and executor runtime classes.
- [`wove.remote`](reference/api/wove.remote.md): callback receiver, payload serialization, and remote worker helpers.
- [`wove.integrations`](reference/api/wove.integrations.md): adapter registry, adapter base interface, and worker entrypoints.

### Backend Adapters

Each adapter page shows the configuration keys, worker setup, and network assumptions for that backend.

- [Celery](reference/executors/celery.md)
- [Temporal](reference/executors/temporal.md)
- [Ray](reference/executors/ray.md)
- [RQ](reference/executors/rq.md)
- [Taskiq](reference/executors/taskiq.md)
- [ARQ](reference/executors/arq.md)
- [Dask](reference/executors/dask.md)
- [Kubernetes Jobs](reference/executors/kubernetes-jobs.md)
- [AWS Batch](reference/executors/aws-batch.md)
- [Slurm](reference/executors/slurm.md)

```{toctree}
:hidden:
:maxdepth: 2

how-to/index
reference/index
```

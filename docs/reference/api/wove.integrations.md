# `wove.integrations`

`wove.integrations` registers built-in backend adapters and provides the adapter base interface. Backend libraries remain optional; Wove includes adapter code but imports third-party packages only when an adapter is selected.

When selected Wove tasks should run through an existing task system, `wove.integrations` provides the adapter registry, the base adapter contract, and the worker entrypoints those systems call to return results to Wove.

All built-in backend adapters are dispatch features. Install `wove[dispatch]` plus the selected backend library in the process that submits work and in any worker environment that executes Wove payloads.

## Adapter Registry

Built-in adapter names:

- `celery`
- `temporal`
- `ray`
- `rq`
- `taskiq`
- `arq`
- `dask`
- `kubernetes_jobs`
- `aws_batch`
- `slurm`

## Adapter Contract

A `BackendAdapter` receives a JSON-safe payload and submits it to a backend. The adapter does not run the task itself. The backend worker must call Wove's worker entrypoint so the result can be posted back to the callback URL.

Required method:

- `submit(payload, frame)`: submit one task payload and return a backend submission handle.

Optional methods:

- `start()`: create clients, queues, pools, or connections.
- `cancel(run_id, submission, frame)`: ask the backend to cancel work.
- `close()`: release adapter-owned clients or pools.

## Worker Entrypoints

- `wove.integrations.worker.run(payload)`: synchronous worker entrypoint.
- `wove.integrations.worker.arun(payload)`: async worker entrypoint.

## Related Pages

- [Backend Adapters](../backend-adapters/index.md): setup pages for the built-in adapters.
- [Custom Backend Adapters](../backend-adapters/custom-backend-adapters.md): implementing an adapter for a project-owned task system.
- [`wove.backend`](wove.backend.md): callback payload and worker callback helpers.

## API Details

```{eval-rst}
.. automodule:: wove.integrations
   :members:

.. automodule:: wove.integrations.base
   :members:

.. automodule:: wove.integrations.worker
   :members:
```

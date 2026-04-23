# `wove.integrations`

`wove.integrations` registers built-in remote adapters and provides the adapter base interface. Backend libraries remain optional; Wove includes adapter code but imports third-party packages only when an adapter is selected.

This package is the adapter layer for existing task systems. It names the built-in integrations, defines the base adapter contract, and exposes the worker functions those systems call to return results to Wove.

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

A `RemoteTaskAdapter` receives a JSON-safe payload and submits it to a backend. It does not run the task itself. The remote worker must call Wove's worker entrypoint so the result can be posted back to the callback URL.

Required method:

- `submit(payload, frame)`: submit one task payload and return a backend submission handle.

Optional methods:

- `start()`: create clients, queues, pools, or connections.
- `cancel(run_id, submission, frame)`: ask the backend to cancel work.
- `close()`: release adapter-owned clients or pools.

## Worker Entrypoints

- `wove.integrations.worker.run(payload)`: synchronous worker entrypoint.
- `wove.integrations.worker.arun(payload)`: async worker entrypoint.

## API Details

```{eval-rst}
.. automodule:: wove.integrations
   :members:

.. automodule:: wove.integrations.base
   :members:

.. automodule:: wove.integrations.worker
   :members:
```

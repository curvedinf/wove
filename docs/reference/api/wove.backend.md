# `wove.backend`

`wove.backend` exposes the backend callback transport and dispatch payload helpers. Backend adapters use this module when a selected task leaves the local weave and runs inside an existing task system such as Celery, Temporal, Ray, Kubernetes, AWS Batch, or Slurm.

The module covers both directions of that movement. `build_backend_payload(...)` turns a ready Wove task frame into a JSON-safe payload for the backend. `BackendCallbackServer` receives worker event frames and hands them back to the original weave so downstream tasks can consume the result.

The callback transport is a dispatch feature. Install `wove[dispatch]` in the submitting process and in worker environments that call these entrypoints.

## Callback Flow

1. `BackendAdapterEnvironmentExecutor` starts `BackendCallbackServer` in the process running the weave.
2. Wove builds a dispatch payload from a ready `run_task` frame. The payload includes the serialized callable, serialized arguments, task identity, run identity, delivery settings, adapter name, and callback URL.
3. The adapter submits that payload to the backend without executing the callable itself.
4. The backend worker receives the payload and calls `wove.integrations.worker.run(payload)` or `await wove.integrations.worker.arun(payload)`.
5. The worker entrypoint executes the callable and posts `task_started`, `task_result`, `task_error`, or `task_cancelled` to the callback URL.
6. `BackendCallbackServer.recv()` returns those frames to the executor runtime, and the original weave resolves the pending task from those frames.

The callback URL points to Wove's callback server, not to an application framework route by default. `callback_host` and `callback_port` control where Wove listens. `callback_url` controls the URL embedded in backend payloads for workers to call.

## Payload Shape

Backend payloads are JSON-safe dictionaries with dispatch-serialized Python values:

- `callable_pickle`: the task callable selected by Wove.
- `args_pickle`: the resolved keyword arguments for that callable.
- `callback_url`: the worker-facing URL for returning events to the weave.
- `run_id` and `task_id`: identifiers Wove uses to match callback events to the pending task.
- `delivery`: delivery policy copied from the task frame.

Worker callback events may carry `result_pickle`, `exception_pickle`, or `error_pickle`. `BackendCallbackServer` deserializes those values before the executor runtime sees the frame.

## Important Functions

- `build_backend_payload(...)`: converts a task frame into a JSON-safe backend payload.
- `run_backend_payload(...)`: synchronous worker entrypoint.
- `run_backend_payload_async(...)`: async worker entrypoint.
- `BackendCallbackServer`: receives callback frames from backend workers.
- `post_event(...)`: posts one event frame to a callback URL.
- `payload_to_b64(...)` and `payload_from_b64(...)`: encode payloads for environment variables or CLI args.

## API Details

```{eval-rst}
.. automodule:: wove.backend
   :members:
```

# `wove.backend`

`wove.backend` exposes the backend callback transport and dispatch payload helpers. Backend adapters use `wove.backend` to serialize task payloads, run them in worker processes, and receive callback frames from backend workers.

When a backend adapter moves work across a process or network boundary, `wove.backend` is the transport layer that turns task frames into worker payloads and worker callbacks back into weave results.

The callback transport is a dispatch feature. Install `wove[dispatch]` in the submitting process and in worker environments that call these entrypoints.

## Callback Flow

1. Wove builds a dispatch payload from a `run_task` frame.
2. The adapter submits that payload to a backend.
3. The backend worker calls `wove.integrations.worker.run(payload)` or `await wove.integrations.worker.arun(payload)`.
4. The worker posts `task_started`, `task_result`, `task_error`, or `task_cancelled` back to the callback URL.
5. `BackendCallbackServer.recv()` returns those frames to the executor runtime.

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

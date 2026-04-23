# `wove.remote`

`wove.remote` is the shared remote execution transport. It serializes task payloads, runs them in worker processes, and receives callback frames from remote task systems.

This module covers the callback transport shared by remote executors: payload serialization, worker entrypoints, event posting, and the receiver that turns backend callbacks back into weave results.

## Callback Flow

1. Wove builds a remote payload from a `run_task` frame.
2. The adapter submits that payload to a backend.
3. The backend worker calls `run_remote_payload(...)` or `run_remote_payload_async(...)`.
4. The worker posts `task_started`, `task_result`, `task_error`, or `task_cancelled` back to the callback URL.
5. `RemoteCallbackServer.recv()` returns those frames to the executor runtime.

## Important Functions

- `build_remote_payload(...)`: converts a task frame into a JSON-safe payload.
- `run_remote_payload(...)`: synchronous worker entrypoint.
- `run_remote_payload_async(...)`: async worker entrypoint.
- `post_event(...)`: posts one event frame to a callback URL.
- `payload_to_b64(...)` and `payload_from_b64(...)`: encode payloads for environment variables or CLI args.

## API Details

```{eval-rst}
.. automodule:: wove.remote
   :members:
```

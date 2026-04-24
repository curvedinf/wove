# Custom Backend Adapters

A custom backend adapter is for a task system your project already runs, but Wove does not ship with yet. The backend owns the delivery path: queueing, scheduling, retries, worker placement, batch jobs, or cluster execution. The adapter only teaches Wove how to submit one serialized Wove payload into that system.

That split keeps task code independent from the backend. The weave selects an environment, the adapter submits the payload, and the backend worker calls Wove's worker entrypoint to send the result back to the original weave.

## Adapter Interface

Custom adapters subclass `BackendAdapter`.

```python
class BackendAdapter:
    required_modules = ()
    install_hint = None

    def __init__(self, *, name, config, callback_url, run_config):
        ...

    async def start(self):
        ...

    async def submit(self, payload: dict, frame: dict):
        ...

    async def cancel(self, run_id: str, submission, frame: dict):
        ...

    async def close(self):
        ...
```

`required_modules` lists import names the adapter needs at runtime. Wove checks those modules before the adapter starts.

`install_hint` is the package name Wove shows when a required module is missing.

`start()` creates backend clients, opens queues, or validates configuration.

`submit(payload, frame)` sends one Wove payload to the backend and returns the backend's submission handle. Wove stores that handle and passes it back to `cancel(...)`.

`cancel(...)` asks the backend to cancel the submitted work when Wove delivery policy requires cancellation.

`close()` releases adapter-owned resources.

## Payload Flow

Backend adapters do not execute the task directly. They submit the payload Wove built.

1. Wove serializes the selected task callable, task arguments, delivery settings, and callback URL into `payload`.
2. The adapter submits `payload` to the backend.
3. A backend worker receives `payload`.
4. The worker calls `wove.integrations.worker.run(payload)` or `await wove.integrations.worker.arun(payload)`.
5. The worker entrypoint executes the task and posts the final event frame back to Wove's callback URL.

The callback URL is created by `BackendAdapterEnvironmentExecutor`. For workers on another host, configure `callback_url` so the worker can reach the original Wove process.

## Minimal Adapter

This example shows the adapter shape for a fictional queue client. The important part is that `submit(...)` enqueues the Wove payload unchanged and returns the backend submission handle.

```python
from wove import BackendAdapter


class AcmeQueueAdapter(BackendAdapter):
    required_modules = ("acme_queue",)
    install_hint = "acme-queue"

    async def start(self):
        import acme_queue

        self.client = self.config.get("client")
        if self.client is None:
            self.client = acme_queue.Client(self.config["url"])

        self.queue = self.config.get("queue", "default")

    async def submit(self, payload, frame):
        delivery = frame.get("delivery") or {}
        return await self.client.enqueue(
            self.queue,
            payload,
            job_id=delivery.get("delivery_idempotency_key") or frame["run_id"],
        )

    async def cancel(self, run_id, submission, frame):
        if submission is not None:
            await self.client.cancel(submission)

    async def close(self):
        await self.client.close()
```

The backend worker receives the same `payload` and hands it to Wove.

```python
from wove.integrations.worker import run


def acme_queue_worker(payload):
    return run(payload)
```

Use `arun(payload)` when the backend worker is already async.

```python
from wove.integrations.worker import arun


async def async_acme_queue_worker(payload):
    return await arun(payload)
```

## Configure The Adapter

Custom adapters are selected by wrapping them in `BackendAdapterEnvironmentExecutor` and using that executor instance in an environment definition.

```python
import wove
from wove import BackendAdapterEnvironmentExecutor, weave

executor = BackendAdapterEnvironmentExecutor(
    "acme_queue",
    adapter_class=AcmeQueueAdapter,
)

wove.config(
    default_environment="local",
    environments={
        "local": {"executor": "local"},
        "reports": {
            "executor": executor,
            "executor_config": {
                "url": "acme://queue.internal",
                "queue": "reports",
                "callback_url": "https://api.internal/wove/events/shared-token",
                "callback_token": "shared-token",
            },
            "delivery_timeout": 60.0,
            "delivery_orphan_policy": "requeue",
        },
    },
)

with weave() as w:
    @w.do
    def account_id():
        return "acct_123"

    @w.do(environment="reports")
    def build_report(account_id):
        return {"account_id": account_id, "status": "ready"}
```

Use an executor instance for project-local adapters. The built-in string names are for adapters registered by Wove itself.

## Configuration Keys

These keys are handled by `BackendAdapterEnvironmentExecutor` before the adapter receives its config.

| Key | Effect |
| --- | --- |
| `callback_host` | Local bind host for the callback receiver. Defaults to `127.0.0.1`. |
| `callback_port` | Local bind port for the callback receiver. Defaults to `0`, which asks the OS for an open port. |
| `callback_url` | Public callback URL embedded in submitted payloads. Use this when workers run on another host. |
| `callback_token` | Token used in the callback URL path. Wove generates one when omitted. |

The adapter also receives those keys in `self.config`, along with any backend-specific settings such as queue names, client objects, credentials, or scheduling options.

## Contract Checklist

- Submit the `payload` unchanged so the worker can call Wove's worker entrypoint.
- Return a backend submission handle from `submit(...)` when cancellation or observability needs it.
- Use `frame["run_id"]` or `delivery_idempotency_key` as the backend job id when the backend supports idempotency.
- Keep backend package imports inside `start(...)` or methods so importing Wove does not require backend libraries.
- Set `required_modules` and `install_hint` so missing dependencies fail with a useful install message.
- Configure a reachable `callback_url` whenever workers are outside the submitting process's host or network namespace.
- Install `wove[dispatch]` in both the process that submits work and the worker environment that executes payloads.

## Related Pages

- [Backend Adapters](index.md): built-in adapter flow and supported systems.
- [`wove.integrations`](../api/wove.integrations.md): adapter registry, base interface, and worker entrypoints.
- [`wove.backend`](../api/wove.backend.md): callback payload and worker callback helpers.

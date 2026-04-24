# `wove.environment`

`wove.environment` contains the executor contract and the runtime bridge that sends tasks to local, subprocess, or remote task environments.

When a named environment becomes running work, `wove.environment` defines the contract: executor instances, runtime delivery errors, and the interface custom executors use to plug into Wove.

## Main Types

- `EnvironmentExecutor`: the four-method executor interface: `start`, `send`, `recv`, `stop`.
- `LocalEnvironmentExecutor`: in-process task execution.
- `StdioEnvironmentExecutor`: JSON-lines subprocess executor.
- `HttpEnvironmentExecutor`: direct HTTP/HTTPS network executor.
- `GrpcEnvironmentExecutor`: generic unary gRPC network executor.
- `WebSocketEnvironmentExecutor`: bidirectional WebSocket network executor.
- `BackendAdapterEnvironmentExecutor`: callback-based executor for backend adapters.
- `ExecutorRuntime`: multiplexes task execution across configured environments.

## Public Exceptions

- `MissingDispatchFeatureError`: raised by dispatch-only executors when `wove[dispatch]` is not installed.
- `EnvironmentExecutionError`: wraps a normalized backend error payload.
- `DeliveryTimeoutError`: raised for delivery timeout or heartbeat expiry.
- `DeliveryOrphanedError`: raised when pending backend work is orphaned during shutdown handling.

## Related Pages

- [Executors](../executors/index.md): frame protocol, executor lifecycle, network executors, error payload shape, and cancellation behavior.
- [Custom Executors](../executors/custom-executors.md): implementing the executor interface for project-owned transports.
- [`wove.security`](wove.security.md): network executor request signing and verification helpers.
- [`wove.backend`](wove.backend.md): backend callback transport used by backend adapters.

## API Details

```{eval-rst}
.. automodule:: wove.environment
   :members:
```

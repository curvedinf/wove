# `wove.environment`

`wove.environment` contains the executor contract and the runtime bridge that sends tasks to local, subprocess, or remote execution environments.

This is the contract layer for execution environments. It is where named environments become executor instances, remote delivery errors are normalized, and custom executors plug into Wove.

## Main Types

- `EnvironmentExecutor`: the four-method executor interface: `start`, `send`, `recv`, `stop`.
- `LocalEnvironmentExecutor`: in-process task execution.
- `StdioEnvironmentExecutor`: JSON-lines subprocess executor.
- `RemoteAdapterEnvironmentExecutor`: callback-based executor for task-system adapters.
- `ExecutorRuntime`: multiplexes task execution across configured environments.

## Public Exceptions

- `EnvironmentExecutionError`: wraps a normalized remote error payload.
- `DeliveryTimeoutError`: raised for delivery timeout or heartbeat expiry.
- `DeliveryOrphanedError`: raised when pending remote work is orphaned during shutdown handling.

## Related Pages

- [Executors](../executors/index.md): frame protocol and executor lifecycle.
- [Executor Errors](../executors/executor-errors.md): error payload shape and cancellation behavior.
- [`wove.remote`](wove.remote.md): callback receiver used by remote adapters.

## API Details

```{eval-rst}
.. automodule:: wove.environment
   :members:
```

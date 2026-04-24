# `wove`

Most application code should import from `wove`. The package-level API names the stable entrypoints for declaring a weave, configuring execution environments, handling public exceptions, and using the helper functions that are meant to sit inside task code.

## Primary Entrypoints

- `weave`: the context manager factory used as `with weave() as w:`.
- `Weave`: base class for reusable and inheritable workflow definitions.
- `config`: process-wide runtime configuration function.
- `merge`: runs external callables from inside a weave task, with the same execution options as `@w.do(...)`.

## Public Runtime Types

- `WoveResult`: result object returned by completed weaves.
- `EnvironmentExecutor`: executor interface for custom execution environments.
- `BackendAdapterEnvironmentExecutor`: executor wrapper used by built-in backend adapters.
- `HttpEnvironmentExecutor`: direct HTTP/HTTPS network executor.
- `GrpcEnvironmentExecutor`: generic unary gRPC network executor.
- `WebSocketEnvironmentExecutor`: bidirectional WebSocket network executor.
- `NetworkExecutorSecurity`: request signing and verification helper for network executors.
- `BackendAdapter`: base interface for backend-specific adapters.

## Public Exceptions

- `MissingDispatchFeatureError`: dispatch-only feature was used without `wove[dispatch]`.
- `DeliveryTimeoutError`: backend delivery or heartbeat timeout.
- `DeliveryOrphanedError`: pending backend work became orphaned during shutdown handling.

## Helpers

Import common data-shaping helpers from the package root when glue code would otherwise distract from the task graph: `sync_to_async`, `flatten`, `fold`, `batch`, `undict`, `redict`, and `denone`.

## API Details

```{eval-rst}
.. automodule:: wove
   :members:
   :exclude-members: BackendAdapter
```

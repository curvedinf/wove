# `wove`

`wove` is the public import surface. If an object is exported here, it is intended to be reachable without importing internal modules.

This page is the index of supported top-level imports: the names used in examples, the exceptions that are safe to catch directly, and the helpers intended for direct use.

## Primary Entrypoints

- `weave`: the context manager factory used as `with weave() as w:`.
- `Weave`: base class for reusable and inheritable workflow definitions.
- `config`: process-wide runtime configuration function.
- `merge`: attaches external functions to a weave.

## Public Runtime Types

- `WoveResult`: result object returned by completed weaves.
- `EnvironmentExecutor`: executor interface for custom execution environments.
- `RemoteAdapterEnvironmentExecutor`: executor wrapper used by built-in remote adapters.
- `RemoteTaskAdapter`: base interface for backend-specific remote adapters.

## Public Exceptions

- `DeliveryTimeoutError`: remote delivery or heartbeat timeout.
- `DeliveryOrphanedError`: pending remote work became orphaned during shutdown handling.

## Helpers

The package also exports common data-shaping helpers: `sync_to_async`, `flatten`, `fold`, `batch`, `undict`, `redict`, and `denone`.

## API Details

```{eval-rst}
.. automodule:: wove
   :members:
```

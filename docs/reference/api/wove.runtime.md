# `wove.runtime`

`wove.runtime` owns process-wide configuration. It stores default environments, environment definitions, and global execution defaults used when a weave starts.

This module is the exact reference for `wove.config(...)`: project config discovery, environment registration, default execution options, and the runtime snapshot used when a weave starts.

## Configuration Entry Point

Most users call the public alias:

```python
import wove

wove.config(
    default_environment="default",
    environments={
        "default": {"executor": "local"},
    },
)
```

Calling `wove.config()` with no arguments attempts to load `wove_config.py` from the current directory or one of its parents. Missing config files are ignored during autoload, so projects can opt in gradually.

## Settings Stored Here

- Environment registry: `default_environment`, `environments`.
- Execution defaults: `max_workers`, `background`, `fork`, `retries`, `timeout`, `workers`, `limit_per_minute`, `max_pending`, `error_mode`.
- Delivery defaults: `delivery_timeout`, `delivery_idempotency_key`, `delivery_cancel_mode`, `delivery_heartbeat_seconds`, `delivery_max_in_flight`, `delivery_orphan_policy`.

## Related Pages

- [Environments](../environments/index.md): dictionary shape and precedence rules.
- [`wove.environment`](wove.environment.md): executor runtime and delivery exceptions.

## API Details

```{eval-rst}
.. automodule:: wove.runtime
   :members:
```

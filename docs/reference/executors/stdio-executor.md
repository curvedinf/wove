# `stdio` Executor

`stdio` runs tasks through a subprocess that speaks Wove's JSON-lines frame protocol. It is the simplest custom execution boundary: Wove writes command frames to stdin and reads event frames from stdout.

## Use When

- You want to prototype a custom executor without writing a full backend adapter.
- Work should run in a separate Python process.
- You need a process boundary but not a broker-backed task system.
- You want to build or debug a custom gateway using streams.

## Configure Wove

```python
import wove

wove.config(
    default_environment="gateway",
    environments={
        "gateway": {
            "executor": "stdio",
            "executor_config": {
                "command": ["python", "-m", "my_gateway"],
            },
        }
    },
)
```

If `executor_config.command` is omitted, Wove launches the built-in gateway:

```bash
python -m wove.gateway
```

## Gateway Responsibilities

A gateway process must:

- Read one JSON command frame per line from stdin.
- Decode task callables and args from Wove's serialized frame fields.
- Execute or forward the task.
- Write one JSON event frame per line to stdout.
- Emit `task_error` frames for task or transport failures.

## Built-In Gateway

The built-in gateway runs the task in the subprocess and emits the normal frame set. It is useful as a reference implementation for custom stream-based executors.

## Related Pages

- [Executors](index.md): full frame contract.
- [`wove.environment`](../api/wove.environment.md): `StdioEnvironmentExecutor` implementation.

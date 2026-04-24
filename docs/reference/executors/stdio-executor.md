# `stdio` Executor

`stdio` runs tasks through a subprocess that speaks Wove's JSON-lines frame protocol. It is the simplest custom execution boundary: Wove writes command frames to stdin and reads event frames from stdout.

## Use When

- You want to prototype a custom executor without writing a full backend adapter.
- Work should run in a separate Python process.
- You need a process boundary but not a broker-backed task system.
- You want to build or debug a custom worker process using streams.

## Dependency

`stdio` is a dispatch feature because Wove serializes task frames across a worker process.

```bash
pip install "wove[dispatch]"
```

## Configure Wove

```python
import wove

wove.config(
    default_environment="worker",
    environments={
        "worker": {
            "executor": "stdio",
            "executor_config": {
                "command": ["python", "-m", "my_worker"],
            },
        }
    },
)
```

If `executor_config.command` is omitted, Wove launches the built-in stdio worker:

```bash
python -m wove.stdio_worker
```

## Worker Process Responsibilities

A worker process must:

- Read one JSON command frame per line from stdin.
- Decode task callables and args from Wove's serialized frame fields.
- Execute or forward the task.
- Write one JSON event frame per line to stdout.
- Emit `task_error` frames for task or transport failures.

## Built-In Worker

The built-in stdio worker runs the task in the subprocess and emits the normal frame set. It is useful as a reference implementation for custom stream-based executors. Its module path remains `python -m wove.stdio_worker`.

## Related Pages

- [Executors](index.md): full frame contract.
- [`wove.environment`](../api/wove.environment.md): `StdioEnvironmentExecutor` implementation.

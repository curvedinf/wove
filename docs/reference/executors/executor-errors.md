# Executor Errors

Executor errors are normalized so Wove can treat local exceptions, subprocess failures, and remote task-system failures consistently.

## Normalized Error Frame

Executors should report task failures with `task_error`.

```python
{
    "type": "task_error",
    "run_id": "task_name:uuid",
    "task_id": "task_name",
    "error": {
        "kind": "TimeoutError",
        "message": "Task timed out",
        "traceback": "...",
        "retryable": True,
        "source": "task",
    },
}
```

In-process executors may also include an `exception` object. Remote executors usually send a pickled exception payload. Wove converts normalized remote error payloads into `EnvironmentExecutionError` when needed.

## Error Sources

| Source | Meaning |
| --- | --- |
| `task` | User task code raised an exception. |
| `executor` | Executor implementation failed while handling a frame. |
| `transport` | Subprocess, callback, queue, or network delivery failed. |
| `config` | Executor or environment configuration is invalid. |

## Public Delivery Exceptions

| Exception | Raised when |
| --- | --- |
| `DeliveryTimeoutError` | `delivery_timeout` is exceeded or heartbeat expiry triggers timeout handling. |
| `DeliveryOrphanedError` | Pending remote work is orphaned while the runtime is stopping. |
| `EnvironmentExecutionError` | A normalized remote error needs to surface as an exception. |

## Cancellation Contract

Wove sends `cancel_task` when delivery timeout, heartbeat timeout, explicit cancellation, or orphan handling requires cancellation.

```python
{
    "type": "cancel_task",
    "run_id": "task_name:uuid",
    "task_id": "task_name",
    "delivery_cancel_mode": "best_effort",
    "delivery_orphan_policy": "requeue",
}
```

Executor responsibility:

- `best_effort`: attempt backend cancellation if the backend supports it.
- `require_ack`: emit `task_cancelled` only after cancellation is known to have succeeded.
- Orphan policies are hints for shutdown handling and backend cleanup.

## Related Pages

- [Executors](index.md): frame protocol and lifecycle.
- [Environments](../environments/index.md): delivery policy configuration.

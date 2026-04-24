# `wove.security`

`wove.security` contains the shared security helper used by Wove's network executors. Most projects only need the `security` setting in an environment definition; worker-service implementers can use `NetworkExecutorSecurity` to validate incoming Wove requests before deserializing task payloads.

## Normal Configuration

Use an environment variable when the submitting process and worker service share a secret:

```python
wove.config(
    environments={
        "workers": {
            "executor": "https",
            "executor_config": {
                "url": "https://workers.internal/wove/tasks",
                "security": "env:WOVE_WORKER_SECRET",
            },
        }
    },
)
```

That shorthand creates signed network executor requests. Wove signs the serialized command body with HMAC-SHA256 and sends the signature as transport-appropriate headers or metadata.

## Security Guarantee

Signed network executor requests authenticate the Wove process that submitted the command frame and detect payload tampering. Each signature covers the transport name, target path or method, timestamp, nonce, and SHA-256 hash of the serialized command body.

The nonce cache rejects replayed signed requests within the configured clock-skew window. TLS is still responsible for confidentiality, which is why Wove requires secure non-local network executor transports unless `executor_config.insecure=True` is set for development.

## Worker Service Verification

A worker service should verify the request before decoding dispatched callables or arguments.

```python
from wove.security import NetworkExecutorSecurity

security = NetworkExecutorSecurity.from_config("env:WOVE_WORKER_SECRET")

# HTTP handler example
raw_body = request.body
security.verify_headers(
    headers=request.headers,
    transport="http",
    target=request.path,
    body=raw_body,
)
```

For gRPC, use `verify_metadata(...)` with the method path as the target.

## Supported Modes

| Shape | Meaning |
| --- | --- |
| `"env:WOVE_WORKER_SECRET"` | Signed requests using a secret stored in an environment variable. |
| `{"type": "signed", "secret_env": "WOVE_WORKER_SECRET"}` | Explicit signed mode. |
| `{"type": "signed", "secret": "..."}` | Signed mode with an inline secret. Useful in tests. |
| `{"type": "bearer", "token_env": "WOVE_WORKER_TOKEN"}` | Bearer token mode for existing worker services. |
| `{"type": "none"}` | No network executor authentication. Only appropriate for local development. |

## API Details

```{eval-rst}
.. automodule:: wove.security
   :members:
```

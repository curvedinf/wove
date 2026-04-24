import hashlib
import hmac
import os
import secrets
import time
import urllib.parse
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


_SIGNED_HEADERS = {
    "key": "X-Wove-Key",
    "timestamp": "X-Wove-Timestamp",
    "nonce": "X-Wove-Nonce",
    "signature": "X-Wove-Signature",
}

__all__ = ["NetworkExecutorSecurity"]


class NetworkExecutorSecurity:
    """
    Authentication helper for Wove network executors.
    """

    def __init__(
        self,
        *,
        mode: str = "none",
        secret: Optional[Any] = None,
        key: str = "default",
        token: Optional[str] = None,
        clock_skew_seconds: float = 300.0,
        remember_nonces: bool = True,
    ) -> None:
        if mode not in {"none", "signed", "bearer"}:
            raise ValueError("network executor security type must be one of: 'none', 'signed', 'bearer'")
        self.mode = mode
        self.key = key
        self.token = str(token) if token is not None else None
        self.clock_skew_seconds = float(clock_skew_seconds)
        self.remember_nonces = remember_nonces
        self._seen_nonces: Dict[str, float] = {}

        if mode == "signed":
            if secret is None:
                raise ValueError("signed network executor security requires a secret.")
            self.secret = secret if isinstance(secret, bytes) else str(secret).encode("utf-8")
        else:
            self.secret = b""

        if mode == "bearer" and not self.token:
            raise ValueError("bearer network executor security requires a token.")

    @classmethod
    def from_config(cls, config: Any) -> "NetworkExecutorSecurity":
        """
        Build network executor security from an executor ``security`` config value.
        """

        if config is None:
            return cls()
        if isinstance(config, str):
            if config == "none":
                return cls()
            if config.startswith("env:"):
                return cls._from_signed_env(config[4:])
            raise ValueError("executor_config.security string must be 'none' or 'env:VARIABLE'.")
        if not isinstance(config, dict):
            raise TypeError("executor_config.security must be a dictionary, 'env:VARIABLE', or 'none'.")

        mode = config.get("type", "signed")
        if mode == "none":
            return cls()
        if mode == "signed":
            secret = config.get("secret")
            secret_env = config.get("secret_env")
            if secret is None and secret_env:
                secret = cls._read_env(secret_env, "network executor security secret")
            return cls(
                mode="signed",
                secret=secret,
                key=str(config.get("key", "default")),
                clock_skew_seconds=float(config.get("clock_skew_seconds", 300.0)),
                remember_nonces=bool(config.get("remember_nonces", True)),
            )
        if mode == "bearer":
            token = config.get("token")
            token_env = config.get("token_env")
            if token is None and token_env:
                token = cls._read_env(token_env, "network executor bearer token")
            return cls(mode="bearer", token=token)
        raise ValueError("executor_config.security.type must be one of: 'signed', 'bearer', 'none'.")

    @classmethod
    def _from_signed_env(cls, env_name: str) -> "NetworkExecutorSecurity":
        if not env_name:
            raise ValueError("network executor security env reference must name an environment variable.")
        return cls(mode="signed", secret=cls._read_env(env_name, "network executor security secret"))

    @staticmethod
    def _read_env(env_name: str, label: str) -> str:
        value = os.environ.get(str(env_name))
        if not value:
            raise RuntimeError(f"{label} environment variable '{env_name}' is not set.")
        return value

    def headers_for(self, *, transport: str, target: str, body: bytes) -> Dict[str, str]:
        """
        Return HTTP/WebSocket headers for one outbound network executor request.
        """

        if self.mode == "none":
            return {}
        if self.mode == "bearer":
            return {"Authorization": f"Bearer {self.token}"}

        timestamp = str(int(time.time()))
        nonce = secrets.token_urlsafe(18)
        signature = self._signature(transport=transport, target=target, body=body, timestamp=timestamp, nonce=nonce)
        return {
            _SIGNED_HEADERS["key"]: self.key,
            _SIGNED_HEADERS["timestamp"]: timestamp,
            _SIGNED_HEADERS["nonce"]: nonce,
            _SIGNED_HEADERS["signature"]: signature,
        }

    def metadata_for(self, *, transport: str, target: str, body: bytes) -> Tuple[Tuple[str, str], ...]:
        """
        Return lowercase gRPC metadata pairs for one outbound network executor request.
        """

        headers = self.headers_for(transport=transport, target=target, body=body)
        return tuple((key.lower(), value) for key, value in headers.items())

    def verify_headers(
        self,
        *,
        headers: Mapping[str, Any],
        transport: str,
        target: str,
        body: bytes,
    ) -> None:
        """
        Verify HTTP/WebSocket network executor request headers.
        """

        normalized = {str(key).lower(): str(value) for key, value in headers.items()}
        self._verify_mapping(normalized, transport=transport, target=target, body=body)

    def verify_metadata(
        self,
        *,
        metadata: Iterable[Tuple[str, Any]],
        transport: str,
        target: str,
        body: bytes,
    ) -> None:
        """
        Verify gRPC network executor request metadata.
        """

        normalized = {str(key).lower(): str(value) for key, value in metadata}
        self._verify_mapping(normalized, transport=transport, target=target, body=body)

    def _verify_mapping(self, values: Dict[str, str], *, transport: str, target: str, body: bytes) -> None:
        if self.mode == "none":
            return
        if self.mode == "bearer":
            expected = f"Bearer {self.token}"
            actual = values.get("authorization")
            if not hmac.compare_digest(actual or "", expected):
                raise PermissionError("Invalid Wove network executor bearer token.")
            return

        timestamp = values.get(_SIGNED_HEADERS["timestamp"].lower())
        nonce = values.get(_SIGNED_HEADERS["nonce"].lower())
        signature = values.get(_SIGNED_HEADERS["signature"].lower())
        key = values.get(_SIGNED_HEADERS["key"].lower())
        if not timestamp or not nonce or not signature or not key:
            raise PermissionError("Missing Wove network executor signature headers.")
        if key != self.key:
            raise PermissionError("Invalid Wove network executor key.")

        try:
            timestamp_value = float(timestamp)
        except ValueError as exc:
            raise PermissionError("Invalid Wove network executor timestamp.") from exc

        if abs(time.time() - timestamp_value) > self.clock_skew_seconds:
            raise PermissionError("Expired Wove network executor signature.")
        expected = self._signature(
            transport=transport,
            target=target,
            body=body,
            timestamp=timestamp,
            nonce=nonce,
        )
        if not hmac.compare_digest(signature, expected):
            raise PermissionError("Invalid Wove network executor signature.")
        self._check_nonce(nonce, timestamp_value)

    def _check_nonce(self, nonce: str, timestamp: float) -> None:
        if not self.remember_nonces:
            return
        cutoff = time.time() - self.clock_skew_seconds
        for seen_nonce, seen_at in list(self._seen_nonces.items()):
            if seen_at < cutoff:
                self._seen_nonces.pop(seen_nonce, None)
        if nonce in self._seen_nonces:
            raise PermissionError("Replayed Wove network executor signature.")
        self._seen_nonces[nonce] = timestamp

    def _signature(self, *, transport: str, target: str, body: bytes, timestamp: str, nonce: str) -> str:
        body_hash = hashlib.sha256(body).hexdigest()
        canonical = "\n".join(["wove-v1", transport, target, timestamp, nonce, body_hash])
        digest = hmac.new(self.secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"v1={digest}"


def _canonical_http_target(url_or_path: str) -> str:
    parsed = urllib.parse.urlsplit(url_or_path)
    if parsed.scheme or parsed.netloc:
        path = parsed.path or "/"
        return f"{path}?{parsed.query}" if parsed.query else path
    return url_or_path or "/"


def _is_local_http_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return _is_local_host(parsed.hostname)


def _is_local_grpc_target(target: str) -> bool:
    target = target.strip()
    if target.startswith(("unix:", "unix-abstract:")):
        return True
    if "://" in target:
        parsed = urllib.parse.urlsplit(target)
        if parsed.scheme.startswith("unix"):
            return True
        host = parsed.hostname
        if host is None and parsed.path:
            host = _endpoint_host(parsed.path.lstrip("/").split("/", 1)[0])
        return _is_local_host(host)
    for prefix in ("dns:", "ipv4:", "ipv6:"):
        if target.startswith(prefix):
            target = target[len(prefix) :]
            break
    host = _endpoint_host(target.rsplit("@", 1)[-1].split("/", 1)[0])
    return _is_local_host(host)


def _ensure_network_executor_security(
    *,
    executor_name: str,
    security: NetworkExecutorSecurity,
    secure_transport: bool,
    local_target: bool,
    insecure: bool,
) -> None:
    if insecure:
        return
    if not secure_transport and not local_target:
        raise ValueError(
            f"{executor_name} executor uses an insecure network transport. "
            "Use TLS or set executor_config.insecure=True for development."
        )
    if security.mode == "none" and not local_target:
        raise ValueError(
            f"{executor_name} executor requires executor_config.security for non-local endpoints. "
            "Use security='env:VARIABLE' or set executor_config.insecure=True for development."
        )


def _is_local_host(host: Optional[str]) -> bool:
    if host is None:
        return False
    return host.strip("[]").lower() in {"localhost", "127.0.0.1", "::1"}


def _endpoint_host(endpoint: str) -> str:
    if endpoint.startswith("[") and "]" in endpoint:
        return endpoint[1:].split("]", 1)[0]
    if endpoint.count(":") == 1:
        return endpoint.rsplit(":", 1)[0]
    return endpoint

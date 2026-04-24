import abc
import asyncio
import base64
import inspect
import importlib
import importlib.util
import json
import shlex
import sys
import time
import traceback
import urllib.parse
import urllib.request
from asyncio.subprocess import Process
from typing import Any, Dict, Optional, Set, Tuple, Type
from uuid import uuid4

from .integrations import (
    get_backend_adapter_class,
    get_backend_adapter_dependencies,
    get_backend_adapter_install_hints,
)
from .integrations.base import BackendAdapter
from .backend import BackendCallbackServer, build_backend_payload
from .security import (
    NetworkExecutorSecurity,
    _canonical_http_target,
    _ensure_network_executor_security,
    _is_local_grpc_target,
    _is_local_http_url,
)
from .serialization import dispatch_dumps, dispatch_loads, require_dispatch

_BACKEND_ADAPTER_DEPENDENCIES: Dict[str, Tuple[str, ...]] = get_backend_adapter_dependencies()
_BACKEND_ADAPTER_INSTALL_HINTS: Dict[str, str] = get_backend_adapter_install_hints()
_KNOWN_ORPHAN_POLICIES: Set[str] = {"fail", "cancel", "requeue", "detach"}
_KNOWN_CANCEL_MODES: Set[str] = {"best_effort", "require_ack"}
_GRPC_DEFAULT_METHOD = "/wove.network_executor.WorkerService/Send"


class EnvironmentExecutionError(RuntimeError):
    """
    Error raised when an executor reports a normalized error payload.
    """

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload
        message = payload.get("message", "Task execution failed.")
        super().__init__(message)


class DeliveryTimeoutError(RuntimeError):
    """
    Raised when backend delivery does not complete within configured delivery_timeout.
    """


class DeliveryOrphanedError(RuntimeError):
    """
    Raised when a backend run becomes orphaned during runtime shutdown/failure handling.
    """


def normalize_exception(
    exc: BaseException,
    *,
    source: str = "task",
    retryable: bool = False,
) -> Dict[str, Any]:
    return {
        "kind": type(exc).__name__,
        "message": str(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        "retryable": retryable,
        "source": source,
    }


def _network_dispatch_reason(executor_name: str) -> str:
    return (
        f"the {executor_name} network executor serializes task frames for a remote worker service."
    )


def _encode_dispatch_value(value: Any, *, reason: str) -> str:
    return base64.b64encode(dispatch_dumps(value, reason=reason)).decode("ascii")


def _decode_dispatch_value(value: str, *, reason: str) -> Any:
    return dispatch_loads(base64.b64decode(value.encode("ascii")), reason=reason)


def _serialize_network_executor_frame(frame: Dict[str, Any], *, reason: str) -> Dict[str, Any]:
    payload = dict(frame)
    if "callable" in payload:
        payload["callable_pickle"] = _encode_dispatch_value(payload.pop("callable"), reason=reason)
    if "args" in payload:
        payload["args_pickle"] = _encode_dispatch_value(payload.pop("args"), reason=reason)
    if "result" in payload:
        payload["result_pickle"] = _encode_dispatch_value(payload.pop("result"), reason=reason)
    if "exception" in payload:
        payload["exception_pickle"] = _encode_dispatch_value(payload.pop("exception"), reason=reason)
    if "error" in payload:
        payload["error_pickle"] = _encode_dispatch_value(payload.pop("error"), reason=reason)
    return payload


def _deserialize_network_executor_frame(payload: Dict[str, Any], *, reason: str) -> Dict[str, Any]:
    frame = dict(payload)
    if "callable_pickle" in frame:
        frame["callable"] = _decode_dispatch_value(frame.pop("callable_pickle"), reason=reason)
    if "args_pickle" in frame:
        frame["args"] = _decode_dispatch_value(frame.pop("args_pickle"), reason=reason)
    if "result_pickle" in frame:
        frame["result"] = _decode_dispatch_value(frame.pop("result_pickle"), reason=reason)
    if "exception_pickle" in frame:
        frame["exception"] = _decode_dispatch_value(frame.pop("exception_pickle"), reason=reason)
    if "error_pickle" in frame:
        frame["error"] = _decode_dispatch_value(frame.pop("error_pickle"), reason=reason)
    return frame


def _dump_network_executor_message(frame: Dict[str, Any], *, reason: str) -> bytes:
    payload = _serialize_network_executor_frame(frame, reason=reason)
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _load_network_executor_events(data: Any, *, reason: str) -> Tuple[Dict[str, Any], ...]:
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    if isinstance(data, str):
        data = json.loads(data)

    if isinstance(data, dict) and "events" in data:
        raw_events = data["events"]
    elif isinstance(data, list):
        raw_events = data
    else:
        raw_events = [data]

    if not isinstance(raw_events, list):
        raise TypeError("Network executor response events must be a list.")

    events = []
    for raw_event in raw_events:
        if not isinstance(raw_event, dict):
            raise TypeError("Network executor events must be dictionaries.")
        events.append(_deserialize_network_executor_frame(raw_event, reason=reason))
    return tuple(events)


def _normalize_headers(headers: Any) -> Dict[str, str]:
    if headers is None:
        return {}
    elif isinstance(headers, dict):
        return {str(key): str(value) for key, value in headers.items()}
    else:
        raise TypeError("executor_config.headers must be a dictionary.")


def _normalize_metadata(metadata: Any) -> Tuple[Tuple[str, str], ...]:
    if metadata is None:
        return ()
    elif isinstance(metadata, dict):
        return tuple((str(key), str(value)) for key, value in metadata.items())
    elif isinstance(metadata, (list, tuple)):
        return tuple((str(key), str(value)) for key, value in metadata)
    else:
        raise TypeError("executor_config.metadata must be a dictionary or sequence of pairs.")


def _require_optional_module(module_name: str, *, executor_name: str, install_hint: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError(
            f"{executor_name} executor requested, but dependency `{module_name}` is not installed. "
            f"Install with: pip install {install_hint}"
        ) from exc


def _transport_error_frame(command: Dict[str, Any], exc: BaseException) -> Dict[str, Any]:
    return {
        "type": "task_error",
        "run_id": command.get("run_id"),
        "task_id": command.get("task_id"),
        "error": normalize_exception(exc, source="transport", retryable=True),
    }


class EnvironmentExecutor(abc.ABC):
    """
    CGI-like stream transport contract for environment executors.
    """

    @abc.abstractmethod
    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        """
        Initialize a run/session for this executor.
        """

    @abc.abstractmethod
    async def send(self, frame: Dict[str, Any]) -> None:
        """
        Send one command frame.
        """

    @abc.abstractmethod
    async def recv(self) -> Dict[str, Any]:
        """
        Receive one event frame.
        """

    @abc.abstractmethod
    async def stop(self) -> None:
        """
        Stop the executor session and clean up resources.
        """


class LocalEnvironmentExecutor(EnvironmentExecutor):
    """
    In-process executor implementation.
    """

    def __init__(self) -> None:
        self._events: asyncio.Queue = asyncio.Queue()
        self._active_runs: Dict[str, asyncio.Task] = {}

    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        del environment_name, environment_config, run_config

    async def send(self, frame: Dict[str, Any]) -> None:
        frame_type = frame.get("type")
        if frame_type == "run_task":
            run_id = frame["run_id"]
            task_id = frame["task_id"]
            task_func = frame["callable"]
            task_args = frame["args"]
            worker = asyncio.create_task(
                self._execute_task(run_id=run_id, task_id=task_id, task_func=task_func, task_args=task_args)
            )
            self._active_runs[run_id] = worker
            return

        if frame_type == "cancel_task":
            run_id = frame["run_id"]
            task = self._active_runs.get(run_id)
            if task:
                task.cancel()
            return

        if frame_type == "shutdown":
            for active in list(self._active_runs.values()):
                active.cancel()
            return

        raise ValueError(f"Unsupported frame type: {frame_type}")

    async def recv(self) -> Dict[str, Any]:
        return await self._events.get()

    async def stop(self) -> None:
        for task in list(self._active_runs.values()):
            task.cancel()
        if self._active_runs:
            await asyncio.gather(*self._active_runs.values(), return_exceptions=True)
        self._active_runs.clear()

    async def _execute_task(
        self,
        *,
        run_id: str,
        task_id: str,
        task_func: Any,
        task_args: Dict[str, Any],
    ) -> None:
        await self._events.put({"type": "task_started", "run_id": run_id, "task_id": task_id})
        try:
            maybe_result = task_func(**task_args)
            if asyncio.iscoroutine(maybe_result):
                result = await maybe_result
            else:
                result = maybe_result
        except asyncio.CancelledError:
            await self._events.put({"type": "task_cancelled", "run_id": run_id, "task_id": task_id})
        except Exception as exc:
            await self._events.put(
                {
                    "type": "task_error",
                    "run_id": run_id,
                    "task_id": task_id,
                    "exception": exc,
                    "error": normalize_exception(exc, source="task"),
                }
            )
        else:
            await self._events.put({"type": "task_result", "run_id": run_id, "task_id": task_id, "result": result})
        finally:
            self._active_runs.pop(run_id, None)


class StdioEnvironmentExecutor(EnvironmentExecutor):
    """
    Subprocess JSON-lines stream executor.
    """

    def __init__(self) -> None:
        self._process: Optional[Process] = None
        self._write_lock = asyncio.Lock()

    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        del environment_name, run_config
        command = environment_config.get("command")
        if not command:
            command = [sys.executable, "-m", "wove.stdio_worker"]

        if isinstance(command, str):
            command = shlex.split(command)
        if not isinstance(command, list) or not command:
            raise TypeError("executor_config.command must be a non-empty list or command string.")

        require_dispatch("the stdio executor serializes task frames across a worker process.")
        self._process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,
        )

    async def send(self, frame: Dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("Stdio executor is not started.")
        payload = self._serialize_frame(frame)
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        async with self._write_lock:
            self._process.stdin.write(data)
            await self._process.stdin.drain()

    async def recv(self) -> Dict[str, Any]:
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("Stdio executor is not started.")
        raw = await self._process.stdout.readline()
        if not raw:
            raise RuntimeError("Worker process closed stdout unexpectedly.")
        payload = json.loads(raw.decode("utf-8"))
        return self._deserialize_frame(payload)

    async def stop(self) -> None:
        if self._process is None:
            return
        if self._process.returncode is None:
            try:
                await self.send({"type": "shutdown"})
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._process.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                self._process.terminate()
                await self._process.wait()
        self._process = None

    def _serialize_frame(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(frame)
        if "callable" in payload:
            payload["callable_pickle"] = base64.b64encode(
                dispatch_dumps(
                    payload.pop("callable"),
                    reason="the stdio executor serializes task callables across a worker process.",
                )
            ).decode("ascii")
        if "args" in payload:
            payload["args_pickle"] = base64.b64encode(
                dispatch_dumps(
                    payload.pop("args"),
                    reason="the stdio executor serializes task arguments across a worker process.",
                )
            ).decode("ascii")
        return payload

    def _deserialize_frame(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        frame = dict(payload)
        if "result_pickle" in frame:
            frame["result"] = dispatch_loads(
                base64.b64decode(frame.pop("result_pickle")),
                reason="the stdio executor deserializes task results from a worker process.",
            )
        if "exception_pickle" in frame:
            frame["exception"] = dispatch_loads(
                base64.b64decode(frame.pop("exception_pickle")),
                reason="the stdio executor deserializes task exceptions from a worker process.",
            )
        if "error_pickle" in frame:
            frame["error"] = dispatch_loads(
                base64.b64decode(frame.pop("error_pickle")),
                reason="the stdio executor deserializes normalized task errors from a worker process.",
            )
        return frame


class HttpEnvironmentExecutor(EnvironmentExecutor):
    """
    Network executor that sends Wove frames to a worker service over HTTP or HTTPS.
    """

    def __init__(self, *, require_https: bool = False) -> None:
        self._require_https = require_https
        self._name = "https" if require_https else "http"
        self._url: Optional[str] = None
        self._headers: Dict[str, str] = {}
        self._security = NetworkExecutorSecurity()
        self._timeout: Optional[float] = None
        self._events: asyncio.Queue = asyncio.Queue()
        self._requests: Dict[str, asyncio.Task] = {}

    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        del environment_name, run_config
        require_dispatch(_network_dispatch_reason(self._name))

        url = environment_config.get("url")
        if not isinstance(url, str) or not url:
            raise TypeError("executor_config.url must be a non-empty HTTP or HTTPS URL.")

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("executor_config.url must be an HTTP or HTTPS URL.")
        if self._require_https and parsed.scheme != "https":
            raise ValueError("The https executor requires an https:// URL.")

        self._security = NetworkExecutorSecurity.from_config(environment_config.get("security"))
        _ensure_network_executor_security(
            executor_name=self._name,
            security=self._security,
            secure_transport=parsed.scheme == "https",
            local_target=_is_local_http_url(url),
            insecure=bool(environment_config.get("insecure", False)),
        )
        self._url = url
        self._headers = _normalize_headers(environment_config.get("headers"))
        timeout = environment_config.get("timeout")
        self._timeout = float(timeout) if timeout is not None else None

    async def send(self, frame: Dict[str, Any]) -> None:
        if self._url is None:
            raise RuntimeError(f"{self._name} executor is not started.")

        frame_type = frame.get("type")
        if frame_type in {"run_task", "cancel_task"}:
            tracking_id = self._request_tracking_id(frame)
            request = asyncio.create_task(self._post_frame(frame, tracking_id))
            self._requests[tracking_id] = request
            return

        if frame_type == "shutdown":
            for request in list(self._requests.values()):
                request.cancel()
            return

        raise ValueError(f"Unsupported frame type: {frame_type}")

    async def recv(self) -> Dict[str, Any]:
        if self._url is None:
            raise RuntimeError(f"{self._name} executor is not started.")
        return await self._events.get()

    async def stop(self) -> None:
        for request in list(self._requests.values()):
            request.cancel()
        if self._requests:
            await asyncio.gather(*self._requests.values(), return_exceptions=True)
        self._requests.clear()
        self._url = None

    def _request_tracking_id(self, frame: Dict[str, Any]) -> str:
        run_id = frame.get("run_id")
        if frame.get("type") == "run_task" and isinstance(run_id, str):
            return run_id
        return f"{frame.get('type', 'request')}:{run_id or uuid4().hex}:{uuid4().hex}"

    async def _post_frame(self, frame: Dict[str, Any], tracking_id: str) -> None:
        try:
            response = await asyncio.to_thread(self._post_json, frame)
            if not response:
                if frame.get("type") == "run_task":
                    raise RuntimeError("HTTP worker service returned an empty response.")
                return
            for event in _load_network_executor_events(response, reason=_network_dispatch_reason(self._name)):
                await self._events.put(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if frame.get("run_id"):
                await self._events.put(_transport_error_frame(frame, exc))
        finally:
            self._requests.pop(tracking_id, None)

    def _post_json(self, frame: Dict[str, Any]) -> bytes:
        if self._url is None:
            raise RuntimeError(f"{self._name} executor is not started.")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._headers,
        }
        body = _dump_network_executor_message(frame, reason=_network_dispatch_reason(self._name))
        headers.update(
            self._security.headers_for(
                transport="http",
                target=_canonical_http_target(self._url),
                body=body,
            )
        )
        request = urllib.request.Request(
            self._url,
            data=body,
            method="POST",
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            return response.read()


class GrpcEnvironmentExecutor(EnvironmentExecutor):
    """
    Network executor that sends Wove frames through a generic gRPC method.
    """

    def __init__(self) -> None:
        self._grpc: Any = None
        self._channel: Any = None
        self._rpc: Any = None
        self._method = _GRPC_DEFAULT_METHOD
        self._timeout: Optional[float] = None
        self._metadata: Tuple[Tuple[str, str], ...] = ()
        self._security = NetworkExecutorSecurity()
        self._events: asyncio.Queue = asyncio.Queue()
        self._requests: Dict[str, asyncio.Task] = {}

    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        del environment_name, run_config
        require_dispatch(_network_dispatch_reason("grpc"))
        self._grpc = _require_optional_module("grpc", executor_name="grpc", install_hint='"wove[dispatch]" grpcio')

        target = environment_config.get("target")
        if not isinstance(target, str) or not target:
            raise TypeError("executor_config.target must be a non-empty gRPC target.")

        method = environment_config.get("method", _GRPC_DEFAULT_METHOD)
        if not isinstance(method, str) or not method.startswith("/"):
            raise TypeError("executor_config.method must be a fully-qualified gRPC method path.")

        self._method = method
        timeout = environment_config.get("timeout")
        self._timeout = float(timeout) if timeout is not None else None
        self._metadata = _normalize_metadata(environment_config.get("metadata"))
        self._security = NetworkExecutorSecurity.from_config(environment_config.get("security"))
        secure_channel = bool(environment_config.get("secure"))
        _ensure_network_executor_security(
            executor_name="grpc",
            security=self._security,
            secure_transport=secure_channel,
            local_target=_is_local_grpc_target(target),
            insecure=bool(environment_config.get("insecure", False)),
        )

        if secure_channel:
            root_certificates = environment_config.get("root_certificates")
            if isinstance(root_certificates, str):
                root_certificates = root_certificates.encode("utf-8")
            credentials = self._grpc.ssl_channel_credentials(root_certificates=root_certificates)
            self._channel = self._grpc.aio.secure_channel(target, credentials)
        else:
            self._channel = self._grpc.aio.insecure_channel(target)

        self._rpc = self._channel.unary_unary(
            self._method,
            request_serializer=lambda value: value,
            response_deserializer=lambda value: value,
        )

    async def send(self, frame: Dict[str, Any]) -> None:
        if self._rpc is None:
            raise RuntimeError("grpc executor is not started.")

        frame_type = frame.get("type")
        if frame_type in {"run_task", "cancel_task"}:
            tracking_id = self._request_tracking_id(frame)
            request = asyncio.create_task(self._call_frame(frame, tracking_id))
            self._requests[tracking_id] = request
            return

        if frame_type == "shutdown":
            for request in list(self._requests.values()):
                request.cancel()
            return

        raise ValueError(f"Unsupported frame type: {frame_type}")

    async def recv(self) -> Dict[str, Any]:
        if self._rpc is None:
            raise RuntimeError("grpc executor is not started.")
        return await self._events.get()

    async def stop(self) -> None:
        for request in list(self._requests.values()):
            request.cancel()
        if self._requests:
            await asyncio.gather(*self._requests.values(), return_exceptions=True)
        self._requests.clear()

        if self._channel is not None:
            close_result = self._channel.close()
            if inspect.isawaitable(close_result):
                await close_result
        self._channel = None
        self._rpc = None

    def _request_tracking_id(self, frame: Dict[str, Any]) -> str:
        run_id = frame.get("run_id")
        if frame.get("type") == "run_task" and isinstance(run_id, str):
            return run_id
        return f"{frame.get('type', 'request')}:{run_id or uuid4().hex}:{uuid4().hex}"

    async def _call_frame(self, frame: Dict[str, Any], tracking_id: str) -> None:
        try:
            kwargs: Dict[str, Any] = {}
            if self._timeout is not None:
                kwargs["timeout"] = self._timeout
            request = _dump_network_executor_message(frame, reason=_network_dispatch_reason("grpc"))
            metadata = (
                *self._metadata,
                *self._security.metadata_for(transport="grpc", target=self._method, body=request),
            )
            if metadata:
                kwargs["metadata"] = metadata

            response = await self._rpc(
                request,
                **kwargs,
            )
            if not response:
                if frame.get("type") == "run_task":
                    raise RuntimeError("gRPC worker service returned an empty response.")
                return
            for event in _load_network_executor_events(response, reason=_network_dispatch_reason("grpc")):
                await self._events.put(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if frame.get("run_id"):
                await self._events.put(_transport_error_frame(frame, exc))
        finally:
            self._requests.pop(tracking_id, None)


class WebSocketEnvironmentExecutor(EnvironmentExecutor):
    """
    Network executor that exchanges Wove frames with a worker service over WebSocket.
    """

    def __init__(self) -> None:
        self._websockets: Any = None
        self._websocket: Any = None
        self._url: Optional[str] = None
        self._headers: Dict[str, str] = {}
        self._security = NetworkExecutorSecurity()
        self._events: asyncio.Queue = asyncio.Queue()

    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        del environment_name, run_config
        require_dispatch(_network_dispatch_reason("websocket"))
        self._websockets = _require_optional_module(
            "websockets",
            executor_name="websocket",
            install_hint='"wove[dispatch]" websockets',
        )

        url = environment_config.get("url")
        if not isinstance(url, str) or not url:
            raise TypeError("executor_config.url must be a non-empty ws:// or wss:// URL.")

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"ws", "wss"} or not parsed.netloc:
            raise ValueError("executor_config.url must be a ws:// or wss:// URL.")

        self._security = NetworkExecutorSecurity.from_config(environment_config.get("security"))
        _ensure_network_executor_security(
            executor_name="websocket",
            security=self._security,
            secure_transport=parsed.scheme == "wss",
            local_target=_is_local_http_url(url),
            insecure=bool(environment_config.get("insecure", False)),
        )
        self._url = url
        self._headers = _normalize_headers(environment_config.get("headers"))
        await self._connect(environment_config)

    async def send(self, frame: Dict[str, Any]) -> None:
        if self._websocket is None:
            raise RuntimeError("websocket executor is not started.")

        frame_type = frame.get("type")
        if frame_type not in {"run_task", "cancel_task", "shutdown"}:
            raise ValueError(f"Unsupported frame type: {frame_type}")

        payload = _dump_network_executor_message(frame, reason=_network_dispatch_reason("websocket")).decode("utf-8")
        await self._websocket.send(payload)

    async def recv(self) -> Dict[str, Any]:
        if self._websocket is None:
            raise RuntimeError("websocket executor is not started.")

        if self._events.empty():
            message = await self._websocket.recv()
            for event in _load_network_executor_events(message, reason=_network_dispatch_reason("websocket")):
                await self._events.put(event)

        return await self._events.get()

    async def stop(self) -> None:
        if self._websocket is not None:
            close_result = self._websocket.close()
            if inspect.isawaitable(close_result):
                await close_result
        self._websocket = None
        self._url = None

    async def _connect(self, environment_config: Dict[str, Any]) -> None:
        connect_kwargs: Dict[str, Any] = {}
        open_timeout = environment_config.get("open_timeout")
        if open_timeout is not None:
            connect_kwargs["open_timeout"] = float(open_timeout)

        headers = dict(self._headers)
        if self._url is not None:
            headers.update(
                self._security.headers_for(
                    transport="websocket",
                    target=_canonical_http_target(self._url),
                    body=b"",
                )
            )

        if headers:
            try:
                self._websocket = await self._websockets.connect(
                    self._url,
                    additional_headers=headers,
                    **connect_kwargs,
                )
            except TypeError:
                self._websocket = await self._websockets.connect(
                    self._url,
                    extra_headers=headers,
                    **connect_kwargs,
                )
        else:
            self._websocket = await self._websockets.connect(self._url, **connect_kwargs)


class BackendAdapterEnvironmentExecutor(EnvironmentExecutor):
    """
    Executor that submits Wove task payloads to a backend adapter and receives
    worker frames over a callback server.
    """

    def __init__(
        self,
        name: str,
        adapter_class: Optional[Type[BackendAdapter]] = None,
        required_modules: Optional[Tuple[str, ...]] = None,
    ) -> None:
        self._name = name
        self._adapter_class = adapter_class or get_backend_adapter_class(name)
        self._required_modules = required_modules or self._adapter_class.required_modules
        self._callback_server: Optional[BackendCallbackServer] = None
        self._adapter: Optional[BackendAdapter] = None
        self._submissions: Dict[str, Any] = {}

    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        del environment_name
        missing = [module for module in self._required_modules if importlib.util.find_spec(module) is None]
        if missing:
            quoted = ", ".join(f"`{name}`" for name in missing)
            install_hint = _BACKEND_ADAPTER_INSTALL_HINTS.get(self._name, " ".join(missing))
            raise RuntimeError(
                f"{self._name} executor requested, but dependency {quoted} is not installed. "
                f"Install with: pip install {install_hint}"
            )
        require_dispatch(
            f"the {self._name} executor serializes task payloads for execution outside the current process."
        )

        self._callback_server = BackendCallbackServer(
            host=environment_config.get("callback_host", "127.0.0.1"),
            port=environment_config.get("callback_port", 0),
            public_url=environment_config.get("callback_url"),
            token=environment_config.get("callback_token"),
        )
        await self._callback_server.start()
        assert self._callback_server.callback_url is not None
        self._adapter = self._adapter_class(
            name=self._name,
            config=environment_config,
            callback_url=self._callback_server.callback_url,
            run_config=run_config,
        )
        try:
            await self._adapter.start()
        except Exception:
            await self._callback_server.stop()
            self._callback_server = None
            self._adapter = None
            raise

    async def send(self, frame: Dict[str, Any]) -> None:
        if self._adapter is None or self._callback_server is None or self._callback_server.callback_url is None:
            raise RuntimeError(f"{self._name} executor was not started.")

        frame_type = frame.get("type")
        if frame_type == "run_task":
            payload = build_backend_payload(
                frame,
                callback_url=self._callback_server.callback_url,
                adapter=self._name,
            )
            self._submissions[frame["run_id"]] = await self._adapter.submit(payload, frame)
            return

        if frame_type == "cancel_task":
            run_id = frame["run_id"]
            submission = self._submissions.get(run_id)
            await self._adapter.cancel(run_id, submission, frame)
            return

        if frame_type == "shutdown":
            return

        raise ValueError(f"Unsupported frame type: {frame_type}")

    async def recv(self) -> Dict[str, Any]:
        if self._callback_server is None:
            raise RuntimeError(f"{self._name} executor was not started.")
        return await self._callback_server.recv()

    async def stop(self) -> None:
        try:
            if self._adapter is not None:
                await self._adapter.close()
        finally:
            if self._callback_server is not None:
                await self._callback_server.stop()
            self._adapter = None
            self._callback_server = None
            self._submissions.clear()


def build_executor_from_name(name: str) -> EnvironmentExecutor:
    if name == "local":
        return LocalEnvironmentExecutor()
    if name == "stdio":
        return StdioEnvironmentExecutor()
    if name == "http":
        return HttpEnvironmentExecutor()
    if name == "https":
        return HttpEnvironmentExecutor(require_https=True)
    if name == "grpc":
        return GrpcEnvironmentExecutor()
    if name == "websocket":
        return WebSocketEnvironmentExecutor()
    if name in _BACKEND_ADAPTER_DEPENDENCIES:
        return BackendAdapterEnvironmentExecutor(name)
    raise ValueError(f"Unknown executor '{name}'.")


def coerce_executor(executor_value: Any) -> EnvironmentExecutor:
    if isinstance(executor_value, EnvironmentExecutor):
        return executor_value
    if isinstance(executor_value, str):
        return build_executor_from_name(executor_value)
    raise TypeError("Environment 'executor' must be a string or EnvironmentExecutor instance.")


class ExecutorRuntime:
    """
    Multiplexes task execution over environment executors.
    """

    def __init__(self, environment_definitions: Dict[str, Dict[str, Any]], run_config: Dict[str, Any]) -> None:
        self._environment_definitions = environment_definitions
        self._run_config = run_config
        self._executors: Dict[str, EnvironmentExecutor] = {}
        self._recv_tasks: Dict[str, asyncio.Task] = {}
        self._pending: Dict[str, Dict[str, asyncio.Future]] = {}
        self._run_metadata: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._inflight_semaphores: Dict[Tuple[str, int], asyncio.Semaphore] = {}
        self._environment_lock: Optional[asyncio.Lock] = None

    async def start(self) -> None:
        for environment_name, definition in self._environment_definitions.items():
            await self.ensure_environment(environment_name, definition)

    async def ensure_environment(
        self,
        environment_name: str,
        definition: Dict[str, Any],
    ) -> None:
        if environment_name in self._executors:
            return

        if self._environment_lock is None:
            self._environment_lock = asyncio.Lock()

        async with self._environment_lock:
            if environment_name in self._executors:
                return

            self._environment_definitions[environment_name] = definition
            executor = coerce_executor(definition.get("executor", "local"))
            executor_config = definition.get("executor_config") or {}
            await executor.start(
                environment_name=environment_name,
                environment_config=executor_config,
                run_config=self._run_config,
            )
            self._executors[environment_name] = executor
            self._pending[environment_name] = {}
            self._run_metadata[environment_name] = {}
            self._recv_tasks[environment_name] = asyncio.create_task(
                self._recv_loop(environment_name, executor)
            )

    async def stop(self) -> None:
        await self._orphan_pending_futures()

        for environment_name, futures in self._pending.items():
            for run_id, future in list(futures.items()):
                if not future.done():
                    future.set_exception(asyncio.CancelledError())
                futures.pop(run_id, None)
                self._run_metadata.get(environment_name, {}).pop(run_id, None)

        for task in self._recv_tasks.values():
            task.cancel()
        if self._recv_tasks:
            await asyncio.gather(*self._recv_tasks.values(), return_exceptions=True)
        self._recv_tasks.clear()

        for executor in self._executors.values():
            await executor.stop()
        self._executors.clear()
        self._pending.clear()
        self._run_metadata.clear()
        self._inflight_semaphores.clear()

    async def run_task(
        self,
        *,
        task_name: str,
        task_func: Any,
        task_args: Dict[str, Any],
        task_info: Dict[str, Any],
    ) -> Any:
        environment_name = task_info.get("environment")
        if environment_name not in self._executors:
            raise NameError(f"Task '{task_name}' references unknown environment '{environment_name}'.")

        recv_task = self._recv_tasks.get(environment_name)
        if recv_task is not None and recv_task.done():
            if recv_task.cancelled():
                raise RuntimeError(f"Executor receiver for environment '{environment_name}' was cancelled.")
            recv_exc = recv_task.exception()
            if recv_exc is not None:
                raise RuntimeError(
                    f"Executor receiver for environment '{environment_name}' stopped unexpectedly."
                ) from recv_exc
            raise RuntimeError(f"Executor receiver for environment '{environment_name}' is not running.")

        executor = self._executors[environment_name]
        delivery_timeout = task_info.get("delivery_timeout")
        cancel_mode = task_info.get("delivery_cancel_mode") or "best_effort"
        if cancel_mode not in _KNOWN_CANCEL_MODES:
            raise ValueError(
                "delivery_cancel_mode must be one of: 'best_effort', 'require_ack'"
            )
        heartbeat_seconds = task_info.get("delivery_heartbeat_seconds")
        orphan_policy = self._resolve_orphan_policy(environment_name, task_info)
        max_in_flight = task_info.get("delivery_max_in_flight")

        idempotency_key = self._resolve_delivery_idempotency_key(task_info, task_args, task_name)
        delivery = {
            "delivery_timeout": delivery_timeout,
            "delivery_idempotency_key": idempotency_key,
            "delivery_cancel_mode": cancel_mode,
            "delivery_heartbeat_seconds": heartbeat_seconds,
            "delivery_orphan_policy": orphan_policy,
        }
        delivery = {key: value for key, value in delivery.items() if value is not None}

        run_id = f"{task_name}:{uuid4().hex}"
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[environment_name][run_id] = future
        self._run_metadata[environment_name][run_id] = {
            "task_id": task_name,
            "delivery_cancel_mode": cancel_mode,
            "delivery_orphan_policy": orphan_policy,
            "delivery_heartbeat_seconds": heartbeat_seconds,
            "started_at": time.monotonic(),
            "last_heartbeat": time.monotonic(),
        }

        run_frame = {
            "type": "run_task",
            "run_id": run_id,
            "task_id": task_name,
            "callable": task_func,
            "args": task_args,
            "delivery": delivery,
        }
        cancel_frame = {
            "type": "cancel_task",
            "run_id": run_id,
            "task_id": task_name,
            "delivery_cancel_mode": cancel_mode,
            "delivery_orphan_policy": orphan_policy,
        }

        semaphore = self._resolve_inflight_semaphore(environment_name, max_in_flight)
        if semaphore is not None:
            async with semaphore:
                await executor.send(run_frame)
                try:
                    return await self._await_result(
                        environment_name=environment_name,
                        run_id=run_id,
                        future=future,
                        executor=executor,
                        cancel_frame=cancel_frame,
                        delivery_timeout=delivery_timeout,
                        heartbeat_seconds=heartbeat_seconds,
                        task_name=task_name,
                    )
                finally:
                    self._pending[environment_name].pop(run_id, None)
                    self._run_metadata[environment_name].pop(run_id, None)

        try:
            await executor.send(run_frame)
            return await self._await_result(
                environment_name=environment_name,
                run_id=run_id,
                future=future,
                executor=executor,
                cancel_frame=cancel_frame,
                delivery_timeout=delivery_timeout,
                heartbeat_seconds=heartbeat_seconds,
                task_name=task_name,
            )
        finally:
            self._pending[environment_name].pop(run_id, None)
            self._run_metadata[environment_name].pop(run_id, None)

    async def _await_result(
        self,
        *,
        environment_name: str,
        run_id: str,
        future: asyncio.Future,
        executor: EnvironmentExecutor,
        cancel_frame: Dict[str, Any],
        delivery_timeout: Optional[float],
        heartbeat_seconds: Optional[float],
        task_name: str,
    ) -> Any:
        started_at = time.monotonic()
        try:
            while True:
                if future.done():
                    return future.result()

                timeout_window = self._next_wait_timeout(
                    environment_name=environment_name,
                    run_id=run_id,
                    started_at=started_at,
                    delivery_timeout=delivery_timeout,
                    heartbeat_seconds=heartbeat_seconds,
                )

                try:
                    if timeout_window is None:
                        return await future
                    return await asyncio.wait_for(asyncio.shield(future), timeout=timeout_window)
                except asyncio.TimeoutError as exc:
                    timed_out_on_delivery = (
                        delivery_timeout is not None and (time.monotonic() - started_at) >= delivery_timeout
                    )
                    if timed_out_on_delivery:
                        await executor.send(cancel_frame)
                        raise DeliveryTimeoutError(
                            f"Delivery timeout exceeded for task '{task_name}' ({delivery_timeout}s)."
                        ) from exc

                    if heartbeat_seconds is not None:
                        metadata = self._run_metadata.get(environment_name, {}).get(run_id, {})
                        last_heartbeat = metadata.get("last_heartbeat", started_at)
                        if (time.monotonic() - last_heartbeat) >= heartbeat_seconds:
                            await executor.send(cancel_frame)
                            raise DeliveryTimeoutError(
                                f"Delivery heartbeat timed out for task '{task_name}' "
                                f"after {heartbeat_seconds}s without heartbeat."
                            ) from exc
                    continue
        except asyncio.CancelledError:
            await executor.send(cancel_frame)
            raise

    def _next_wait_timeout(
        self,
        *,
        environment_name: str,
        run_id: str,
        started_at: float,
        delivery_timeout: Optional[float],
        heartbeat_seconds: Optional[float],
    ) -> Optional[float]:
        windows = []
        now = time.monotonic()
        if delivery_timeout is not None:
            windows.append(max(delivery_timeout - (now - started_at), 0))

        if heartbeat_seconds is not None:
            metadata = self._run_metadata.get(environment_name, {}).get(run_id, {})
            last_heartbeat = metadata.get("last_heartbeat", started_at)
            windows.append(max(heartbeat_seconds - (now - last_heartbeat), 0))

        if not windows:
            return None
        return min(windows)

    def _resolve_orphan_policy(self, environment_name: str, task_info: Dict[str, Any]) -> str:
        raw_policy = task_info.get("delivery_orphan_policy")
        if raw_policy is None:
            raw_policy = self._environment_definitions.get(environment_name, {}).get("delivery_orphan_policy")
        if raw_policy is None:
            raw_policy = self._run_config.get("delivery_orphan_policy")
        if raw_policy is None:
            return "cancel"
        if raw_policy not in _KNOWN_ORPHAN_POLICIES:
            allowed = "', '".join(sorted(_KNOWN_ORPHAN_POLICIES))
            raise ValueError(f"delivery_orphan_policy must be one of: '{allowed}'")
        return raw_policy

    def _resolve_inflight_semaphore(
        self,
        environment_name: str,
        max_in_flight: Optional[int],
    ) -> Optional[asyncio.Semaphore]:
        if not isinstance(max_in_flight, int) or max_in_flight <= 0:
            return None
        key = (environment_name, max_in_flight)
        semaphore = self._inflight_semaphores.get(key)
        if semaphore is None:
            semaphore = asyncio.Semaphore(max_in_flight)
            self._inflight_semaphores[key] = semaphore
        return semaphore

    async def _orphan_pending_futures(self) -> None:
        for environment_name, futures in self._pending.items():
            executor = self._executors.get(environment_name)
            metadata_map = self._run_metadata.get(environment_name, {})
            for run_id, future in list(futures.items()):
                if future.done():
                    continue

                metadata = metadata_map.get(run_id, {})
                orphan_policy = metadata.get("delivery_orphan_policy", "cancel")
                cancel_mode = metadata.get("delivery_cancel_mode", "best_effort")
                task_id = metadata.get("task_id", run_id)

                if (
                    executor is not None
                    and orphan_policy in {"cancel", "fail", "requeue"}
                ):
                    cancel_frame = {
                        "type": "cancel_task",
                        "run_id": run_id,
                        "task_id": task_id,
                        "delivery_cancel_mode": cancel_mode,
                        "delivery_orphan_policy": orphan_policy,
                    }
                    try:
                        await executor.send(cancel_frame)
                    except Exception:
                        pass

                if orphan_policy == "cancel":
                    future.set_exception(asyncio.CancelledError())
                    continue

                future.set_exception(
                    DeliveryOrphanedError(
                        f"Task '{task_id}' became orphaned in environment '{environment_name}' "
                        f"with policy '{orphan_policy}'."
                    )
                )

    def _resolve_delivery_idempotency_key(
        self,
        task_info: Dict[str, Any],
        task_args: Dict[str, Any],
        task_name: str,
    ) -> Optional[str]:
        raw_key = task_info.get("delivery_idempotency_key")
        if raw_key is None:
            return None

        if callable(raw_key):
            try:
                value = raw_key(task_args)
            except TypeError:
                value = raw_key(**task_args)
            return str(value)

        if isinstance(raw_key, str):
            if "{" in raw_key:
                try:
                    return raw_key.format_map(task_args)
                except KeyError:
                    return raw_key
            return raw_key

        return str(raw_key)

    def is_local_environment(self, environment_name: str) -> bool:
        definition = self._environment_definitions.get(environment_name, {})
        executor_value = definition.get("executor", "local")
        if isinstance(executor_value, str):
            return executor_value == "local"
        return isinstance(executor_value, LocalEnvironmentExecutor)

    async def _recv_loop(self, environment_name: str, executor: EnvironmentExecutor) -> None:
        pending = self._pending[environment_name]
        metadata_map = self._run_metadata[environment_name]
        try:
            while True:
                frame = await executor.recv()
                run_id = frame.get("run_id")
                if not run_id:
                    continue
                future = pending.get(run_id)
                if future is None or future.done():
                    continue

                frame_type = frame.get("type")
                if frame_type == "task_started":
                    if run_id in metadata_map:
                        metadata_map[run_id]["last_heartbeat"] = time.monotonic()
                    continue
                if frame_type == "heartbeat":
                    if run_id in metadata_map:
                        metadata_map[run_id]["last_heartbeat"] = time.monotonic()
                    continue
                if frame_type == "log":
                    continue
                if frame_type == "task_result":
                    future.set_result(frame.get("result"))
                    continue
                if frame_type == "task_cancelled":
                    future.set_exception(asyncio.CancelledError())
                    continue
                if frame_type == "task_error":
                    future.set_exception(self._exception_from_error_frame(frame))
                    continue

                future.set_exception(
                    RuntimeError(
                        f"Unknown executor frame type '{frame_type}' from environment '{environment_name}'."
                    )
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for run_id, future in list(pending.items()):
                if future.done():
                    continue
                orphan_policy = metadata_map.get(run_id, {}).get("delivery_orphan_policy", "cancel")
                if orphan_policy == "cancel":
                    future.set_exception(exc)
                else:
                    future.set_exception(
                        DeliveryOrphanedError(
                            f"Task '{metadata_map.get(run_id, {}).get('task_id', run_id)}' "
                            f"orphaned after receiver failure in environment '{environment_name}' "
                            f"(policy='{orphan_policy}')."
                        )
                    )
            raise

    def _exception_from_error_frame(self, frame: Dict[str, Any]) -> BaseException:
        if "exception" in frame and isinstance(frame["exception"], BaseException):
            return frame["exception"]
        payload = frame.get("error") or {}
        if not isinstance(payload, dict):
            payload = {"message": str(payload), "kind": "ExecutionError", "source": "executor"}
        return EnvironmentExecutionError(payload)

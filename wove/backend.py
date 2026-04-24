import asyncio
import base64
import inspect
import json
import secrets
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from .serialization import dispatch_dumps, dispatch_loads


def _encode_pickle(value: Any) -> str:
    return base64.b64encode(
        dispatch_dumps(
            value,
            reason="dispatch serialization moves task payloads, results, and errors across process or network boundaries.",
        )
    ).decode("ascii")


def _decode_pickle(value: str) -> Any:
    return dispatch_loads(
        base64.b64decode(value.encode("ascii")),
        reason="dispatch serialization moves task payloads, results, and errors across process or network boundaries.",
    )


def serialize_frame(frame: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Wove event frame into a JSON-safe callback payload.
    """

    payload = dict(frame)
    if "result" in payload:
        payload["result_pickle"] = _encode_pickle(payload.pop("result"))
    if "exception" in payload:
        payload["exception_pickle"] = _encode_pickle(payload.pop("exception"))
    if "error" in payload:
        payload["error_pickle"] = _encode_pickle(payload.pop("error"))
    return payload


def deserialize_frame(payload: Dict[str, Any]) -> Dict[str, Any]:
    frame = dict(payload)
    if "result_pickle" in frame:
        frame["result"] = _decode_pickle(frame.pop("result_pickle"))
    if "exception_pickle" in frame:
        frame["exception"] = _decode_pickle(frame.pop("exception_pickle"))
    if "error_pickle" in frame:
        frame["error"] = _decode_pickle(frame.pop("error_pickle"))
    return frame


def payload_to_b64(payload: Dict[str, Any]) -> str:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(data).decode("ascii")


def payload_from_b64(value: str) -> Dict[str, Any]:
    return json.loads(base64.b64decode(value.encode("ascii")).decode("utf-8"))


def build_backend_payload(
    frame: Dict[str, Any],
    *,
    callback_url: str,
    adapter: str,
) -> Dict[str, Any]:
    """
    Build the JSON-safe payload that a backend worker executes.
    """

    return {
        "version": 1,
        "adapter": adapter,
        "callback_url": callback_url,
        "run_id": frame["run_id"],
        "task_id": frame["task_id"],
        "task_name": frame.get("task_name"),
        "callable_pickle": _encode_pickle(frame["callable"]),
        "args_pickle": _encode_pickle(frame["args"]),
        "delivery": frame.get("delivery") or {},
    }


def post_event(callback_url: str, frame: Dict[str, Any], *, timeout: Optional[float] = None) -> None:
    data = json.dumps(serialize_frame(frame), separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        callback_url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()


async def run_backend_payload_async(payload: Dict[str, Any]) -> Any:
    """
    Execute a backend payload and deliver the result to its callback URL.
    """

    callback_url = payload["callback_url"]
    run_id = payload["run_id"]
    task_id = payload["task_id"]
    await asyncio.to_thread(
        post_event,
        callback_url,
        {"type": "task_started", "run_id": run_id, "task_id": task_id},
    )

    try:
        task_func = _decode_pickle(payload["callable_pickle"])
        task_args = _decode_pickle(payload["args_pickle"])
        maybe_result = task_func(**task_args)
        if inspect.isawaitable(maybe_result):
            result = await maybe_result
        else:
            result = maybe_result
    except asyncio.CancelledError:
        frame = {"type": "task_cancelled", "run_id": run_id, "task_id": task_id}
        await asyncio.to_thread(post_event, callback_url, frame)
        return frame
    except Exception as exc:
        from .environment import normalize_exception

        frame = {
            "type": "task_error",
            "run_id": run_id,
            "task_id": task_id,
            "exception": exc,
            "error": normalize_exception(exc, source="task"),
        }
        await asyncio.to_thread(post_event, callback_url, frame)
        return frame

    frame = {"type": "task_result", "run_id": run_id, "task_id": task_id, "result": result}
    await asyncio.to_thread(post_event, callback_url, frame)
    return result


def run_backend_payload(payload: Dict[str, Any]) -> Any:
    """
    Synchronous worker entrypoint for backend workers.
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run_backend_payload_async(payload))
    raise RuntimeError("run_backend_payload_async must be used when already inside an event loop.")


class BackendCallbackServer:
    """
    Small HTTP receiver that turns backend worker callbacks into executor frames.
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        public_url: Optional[str] = None,
        token: Optional[str] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.public_url = public_url
        self.token = token or secrets.token_urlsafe(24)
        self.callback_url: Optional[str] = None
        self._queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    async def start(self) -> None:
        if self._server is not None:
            return

        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                expected_path = f"/wove/events/{owner.token}"
                if self.path != expected_path:
                    self.send_response(404)
                    self.end_headers()
                    return

                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                    frame = deserialize_frame(payload)
                except Exception as exc:
                    body = str(exc).encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                assert owner._loop is not None
                assert owner._queue is not None
                owner._loop.call_soon_threadsafe(owner._queue.put_nowait, frame)
                self.send_response(204)
                self.end_headers()

            def log_message(self, _format: str, *args: Any) -> None:
                return None

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        bound_host, bound_port = self._server.server_address[:2]
        if self.public_url:
            self.callback_url = self.public_url.rstrip("/")
        else:
            self.callback_url = f"http://{bound_host}:{bound_port}/wove/events/{self.token}"

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    async def recv(self) -> Dict[str, Any]:
        if self._queue is None:
            raise RuntimeError("Backend callback server is not started.")
        return await self._queue.get()

    async def stop(self) -> None:
        if self._server is None:
            return
        await asyncio.to_thread(self._server.shutdown)
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._server = None
        self._thread = None
        self._queue = None
        self._loop = None
        self.callback_url = None


__all__ = [
    "BackendCallbackServer",
    "build_backend_payload",
    "deserialize_frame",
    "payload_from_b64",
    "payload_to_b64",
    "post_event",
    "run_backend_payload",
    "run_backend_payload_async",
    "serialize_frame",
]

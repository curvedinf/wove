import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cloudpickle
import pytest

from wove.environment import (
    GrpcEnvironmentExecutor,
    HttpEnvironmentExecutor,
    WebSocketEnvironmentExecutor,
    build_executor_from_name,
)
from wove.security import NetworkExecutorSecurity, _canonical_http_target, _is_local_grpc_target, _is_local_http_url


def _pickle(value):
    import base64

    return base64.b64encode(cloudpickle.dumps(value)).decode("ascii")


def _unpickle(value):
    import base64

    return cloudpickle.loads(base64.b64decode(value.encode("ascii")))


def _run_frame(run_id="r1"):
    return {
        "type": "run_task",
        "run_id": run_id,
        "task_id": "add",
        "callable": lambda a, b: a + b,
        "args": {"a": 2, "b": 3},
        "delivery": {},
    }


@pytest.mark.asyncio
async def test_http_executor_posts_frames_to_worker_service():
    seen = []
    verifier = NetworkExecutorSecurity.from_config({"type": "signed", "secret": "secret"})

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            verifier.verify_headers(headers=self.headers, transport="http", target=self.path, body=raw)
            payload = json.loads(raw.decode("utf-8"))
            seen.append((self.path, self.headers.get("X-Wove-Signature"), payload))

            func = _unpickle(payload["callable_pickle"])
            args = _unpickle(payload["args_pickle"])
            result = func(**args)
            body = json.dumps(
                {
                    "events": [
                        {"type": "task_started", "run_id": payload["run_id"], "task_id": payload["task_id"]},
                        {
                            "type": "task_result",
                            "run_id": payload["run_id"],
                            "task_id": payload["task_id"],
                            "result_pickle": _pickle(result),
                        },
                    ]
                },
                separators=(",", ":"),
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *args):
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/wove"

    executor = HttpEnvironmentExecutor()
    await executor.start(
        environment_name="http",
        environment_config={
            "url": url,
            "security": {"type": "signed", "secret": "secret"},
            "timeout": 2.0,
        },
        run_config={},
    )

    await executor.send(_run_frame())
    started = await asyncio.wait_for(executor.recv(), timeout=1.0)
    result = await asyncio.wait_for(executor.recv(), timeout=1.0)

    assert started["type"] == "task_started"
    assert result["type"] == "task_result"
    assert result["result"] == 5
    assert seen[0][0] == "/wove"
    assert seen[0][1].startswith("v1=")
    assert seen[0][2]["type"] == "run_task"

    await executor.stop()
    await asyncio.to_thread(server.shutdown)
    server.server_close()


@pytest.mark.asyncio
async def test_http_executor_validation_transport_error_and_shutdown(monkeypatch):
    executor = HttpEnvironmentExecutor()
    with pytest.raises(RuntimeError, match="not started"):
        await executor.recv()
    with pytest.raises(RuntimeError, match="not started"):
        await executor.send({"type": "run_task"})
    with pytest.raises(TypeError, match="url"):
        await executor.start(environment_name="http", environment_config={}, run_config={})

    https_executor = HttpEnvironmentExecutor(require_https=True)
    with pytest.raises(ValueError, match="https"):
        await https_executor.start(
            environment_name="https",
            environment_config={"url": "http://example.test/wove"},
            run_config={},
        )

    remote_executor = HttpEnvironmentExecutor()
    with pytest.raises(ValueError, match="requires executor_config.security"):
        await remote_executor.start(
            environment_name="http",
            environment_config={"url": "https://workers.example.test/wove"},
            run_config={},
        )

    with pytest.raises(ValueError, match="insecure network transport"):
        await remote_executor.start(
            environment_name="http",
            environment_config={
                "url": "http://workers.example.test/wove",
                "security": {"type": "signed", "secret": "secret"},
            },
            run_config={},
        )

    await executor.start(
        environment_name="http",
        environment_config={"url": "http://127.0.0.1:9/wove"},
        run_config={},
    )

    def fail(_frame):
        raise OSError("network down")

    monkeypatch.setattr(executor, "_post_json", fail)
    await executor.send(_run_frame("err"))
    err = await asyncio.wait_for(executor.recv(), timeout=1.0)
    assert err["type"] == "task_error"
    assert err["error"]["source"] == "transport"
    assert "network down" in err["error"]["message"]

    async def parked(_frame, _tracking_id):
        await asyncio.sleep(3600)

    monkeypatch.setattr(executor, "_post_frame", parked)
    await executor.send(_run_frame("tracked"))
    await executor.send({"type": "cancel_task", "run_id": "tracked", "task_id": "add"})
    assert len(executor._requests) == 2
    assert "tracked" in executor._requests
    assert any(key.startswith("cancel_task:tracked:") for key in executor._requests)

    await executor.send({"type": "shutdown"})
    with pytest.raises(ValueError, match="Unsupported frame type"):
        await executor.send({"type": "unknown"})
    await executor.stop()


def test_network_executor_name_resolution():
    assert isinstance(build_executor_from_name("http"), HttpEnvironmentExecutor)
    assert isinstance(build_executor_from_name("https"), HttpEnvironmentExecutor)
    assert isinstance(build_executor_from_name("grpc"), GrpcEnvironmentExecutor)
    assert isinstance(build_executor_from_name("websocket"), WebSocketEnvironmentExecutor)


def test_network_executor_security_config_and_verification(monkeypatch):
    monkeypatch.setenv("WOVE_TEST_SECRET", "secret")
    monkeypatch.setenv("WOVE_TEST_TOKEN", "token")
    signer = NetworkExecutorSecurity.from_config("env:WOVE_TEST_SECRET")
    verifier = NetworkExecutorSecurity.from_config({"type": "signed", "secret_env": "WOVE_TEST_SECRET"})
    body = b'{"ok":true}'
    headers = signer.headers_for(transport="http", target="/wove", body=body)
    verifier.verify_headers(headers=headers, transport="http", target="/wove", body=body)

    with pytest.raises(PermissionError, match="Replayed"):
        verifier.verify_headers(headers=headers, transport="http", target="/wove", body=body)

    expired = dict(headers)
    expired["X-Wove-Nonce"] = "different"
    expired["X-Wove-Timestamp"] = "0"
    with pytest.raises(PermissionError, match="Expired"):
        NetworkExecutorSecurity.from_config({"type": "signed", "secret": "secret"}).verify_headers(
            headers=expired,
            transport="http",
            target="/wove",
            body=body,
        )

    bad_signature = signer.headers_for(transport="http", target="/wove", body=body)
    bad_signature["X-Wove-Signature"] = "v1=wrong"
    bad_signature_verifier = NetworkExecutorSecurity.from_config({"type": "signed", "secret": "secret"})
    with pytest.raises(PermissionError, match="Invalid Wove network executor signature"):
        bad_signature_verifier.verify_headers(headers=bad_signature, transport="http", target="/wove", body=body)
    corrected = dict(bad_signature)
    corrected["X-Wove-Signature"] = signer._signature(
        transport="http",
        target="/wove",
        body=body,
        timestamp=corrected["X-Wove-Timestamp"],
        nonce=corrected["X-Wove-Nonce"],
    )
    bad_signature_verifier.verify_headers(headers=corrected, transport="http", target="/wove", body=body)

    no_replay_verifier = NetworkExecutorSecurity.from_config(
        {"type": "signed", "secret": "secret", "remember_nonces": False}
    )
    reusable = signer.headers_for(transport="http", target="/wove", body=body)
    no_replay_verifier.verify_headers(headers=reusable, transport="http", target="/wove", body=body)
    no_replay_verifier.verify_headers(headers=reusable, transport="http", target="/wove", body=body)

    bearer = NetworkExecutorSecurity.from_config({"type": "bearer", "token": "token"})
    bearer.verify_metadata(
        metadata=bearer.metadata_for(transport="grpc", target="/wove.Executor/Send", body=body),
        transport="grpc",
        target="/wove.Executor/Send",
        body=body,
    )
    NetworkExecutorSecurity.from_config({"type": "bearer", "token_env": "WOVE_TEST_TOKEN"})
    with pytest.raises(PermissionError, match="bearer"):
        bearer.verify_headers(headers={"Authorization": "Bearer wrong"}, transport="http", target="/wove", body=body)

    assert NetworkExecutorSecurity.from_config(None).headers_for(transport="http", target="/wove", body=body) == {}
    assert NetworkExecutorSecurity.from_config("none").mode == "none"
    assert NetworkExecutorSecurity.from_config({"type": "none"}).mode == "none"
    assert _canonical_http_target("https://workers.internal/wove/tasks?x=1") == "/wove/tasks?x=1"
    assert _canonical_http_target("") == "/"
    assert _is_local_http_url("http://localhost:8000/wove")
    assert _is_local_grpc_target("localhost:9000")
    assert _is_local_grpc_target("dns:///localhost:9000")
    assert not _is_local_grpc_target("workers:9000")

    with pytest.raises(RuntimeError, match="WOVE_MISSING_SECRET"):
        NetworkExecutorSecurity.from_config("env:WOVE_MISSING_SECRET")
    with pytest.raises(ValueError, match="env reference"):
        NetworkExecutorSecurity.from_config("env:")
    with pytest.raises(ValueError, match="string"):
        NetworkExecutorSecurity.from_config("secret")
    with pytest.raises(ValueError, match="bearer"):
        NetworkExecutorSecurity.from_config({"type": "bearer"})
    with pytest.raises(ValueError, match="signed"):
        NetworkExecutorSecurity(mode="signed")
    with pytest.raises(ValueError, match="network executor security type"):
        NetworkExecutorSecurity(mode="unknown")
    with pytest.raises(ValueError, match="security.type"):
        NetworkExecutorSecurity.from_config({"type": "unknown"})
    with pytest.raises(TypeError, match="security"):
        NetworkExecutorSecurity.from_config(123)


@pytest.mark.asyncio
async def test_grpc_executor_generic_unary_worker_service(monkeypatch):
    captured = {}
    verifier = NetworkExecutorSecurity.from_config({"type": "signed", "secret": "secret"})

    class FakeRpc:
        async def __call__(self, request, **kwargs):
            verifier.verify_metadata(
                metadata=kwargs["metadata"],
                transport="grpc",
                target="/wove.network_executor.WorkerService/Send",
                body=request,
            )
            payload = json.loads(request.decode("utf-8"))
            captured["payload"] = payload
            captured["kwargs"] = kwargs
            return json.dumps(
                [
                    {"type": "task_started", "run_id": payload["run_id"], "task_id": payload["task_id"]},
                    {
                        "type": "task_result",
                        "run_id": payload["run_id"],
                        "task_id": payload["task_id"],
                        "result_pickle": _pickle(11),
                    },
                ],
                separators=(",", ":"),
            ).encode("utf-8")

    class FakeChannel:
        def unary_unary(self, method, request_serializer, response_deserializer):
            captured["method"] = method
            captured["serialized"] = request_serializer(b"x")
            captured["deserialized"] = response_deserializer(b"y")
            return FakeRpc()

        async def close(self):
            captured["closed"] = True

    class FakeAio:
        def secure_channel(self, target, credentials):
            captured["target"] = target
            captured["credentials"] = credentials
            return FakeChannel()

        def insecure_channel(self, target):
            captured["insecure_target"] = target
            return FakeChannel()

    class FakeGrpc:
        aio = FakeAio()

        def ssl_channel_credentials(self, root_certificates=None):
            captured["root_certificates"] = root_certificates
            return "creds"

    monkeypatch.setattr("wove.environment.importlib.import_module", lambda name: FakeGrpc())

    executor = GrpcEnvironmentExecutor()
    await executor.start(
        environment_name="grpc",
        environment_config={
            "target": "workers.internal:9000",
            "method": "/wove.network_executor.WorkerService/Send",
            "secure": True,
            "root_certificates": "certs",
            "metadata": {"x-project": "wove"},
            "security": {"type": "signed", "secret": "secret"},
            "timeout": 4.0,
        },
        run_config={},
    )

    await executor.send(_run_frame("grpc-run"))
    started = await asyncio.wait_for(executor.recv(), timeout=1.0)
    result = await asyncio.wait_for(executor.recv(), timeout=1.0)

    assert started["type"] == "task_started"
    assert result["result"] == 11
    assert captured["target"] == "workers.internal:9000"
    assert captured["root_certificates"] == b"certs"
    assert captured["method"] == "/wove.network_executor.WorkerService/Send"
    assert captured["serialized"] == b"x"
    assert captured["deserialized"] == b"y"
    assert captured["kwargs"]["timeout"] == 4.0
    assert any(key == "x-wove-signature" and value.startswith("v1=") for key, value in captured["kwargs"]["metadata"])
    assert captured["payload"]["type"] == "run_task"

    await executor.stop()
    assert captured["closed"] is True


@pytest.mark.asyncio
async def test_grpc_executor_validation_missing_dependency_and_transport_error(monkeypatch):
    executor = GrpcEnvironmentExecutor()
    with pytest.raises(RuntimeError, match="not started"):
        await executor.recv()
    with pytest.raises(RuntimeError, match="not started"):
        await executor.send({"type": "run_task"})

    def missing(name):
        raise ImportError(name)

    monkeypatch.setattr("wove.environment.importlib.import_module", missing)
    with pytest.raises(RuntimeError, match="grpc executor requested"):
        await executor.start(environment_name="grpc", environment_config={"target": "x"}, run_config={})

    class FakeRpc:
        async def __call__(self, _request, **_kwargs):
            raise OSError("rpc down")

    class FakeChannel:
        def unary_unary(self, *_args, **_kwargs):
            return FakeRpc()

        def close(self):
            return None

    class FakeAio:
        def insecure_channel(self, target):
            return FakeChannel()

    class FakeGrpc:
        aio = FakeAio()

    monkeypatch.setattr("wove.environment.importlib.import_module", lambda name: FakeGrpc())
    with pytest.raises(TypeError, match="target"):
        await executor.start(environment_name="grpc", environment_config={}, run_config={})

    with pytest.raises(ValueError, match="requires executor_config.security"):
        await executor.start(environment_name="grpc", environment_config={"target": "workers:9000", "secure": True}, run_config={})

    with pytest.raises(ValueError, match="insecure network transport"):
        await executor.start(
            environment_name="grpc",
            environment_config={
                "target": "workers:9000",
                "security": {"type": "signed", "secret": "secret"},
            },
            run_config={},
        )

    await executor.start(
        environment_name="grpc",
        environment_config={"target": "workers:9000", "insecure": True},
        run_config={},
    )
    await executor.send(_run_frame("grpc-err"))
    err = await asyncio.wait_for(executor.recv(), timeout=1.0)
    assert err["type"] == "task_error"
    assert err["error"]["source"] == "transport"
    assert "rpc down" in err["error"]["message"]

    async def parked(_frame, _tracking_id):
        await asyncio.sleep(3600)

    monkeypatch.setattr(executor, "_call_frame", parked)
    await executor.send(_run_frame("tracked-grpc"))
    await executor.send({"type": "cancel_task", "run_id": "tracked-grpc", "task_id": "add"})
    assert len(executor._requests) == 2
    assert "tracked-grpc" in executor._requests
    assert any(key.startswith("cancel_task:tracked-grpc:") for key in executor._requests)

    await executor.send({"type": "shutdown"})
    with pytest.raises(ValueError, match="Unsupported frame type"):
        await executor.send({"type": "unknown"})
    await executor.stop()


@pytest.mark.asyncio
async def test_websocket_executor_sends_and_receives_worker_frames(monkeypatch):
    captured = {}
    verifier = NetworkExecutorSecurity.from_config({"type": "signed", "secret": "secret"})

    class FakeSocket:
        def __init__(self):
            self.sent = []
            self.incoming = asyncio.Queue()
            self.closed = False

        async def send(self, message):
            self.sent.append(json.loads(message))

        async def recv(self):
            return await self.incoming.get()

        async def close(self):
            self.closed = True

    fake_socket = FakeSocket()

    class FakeWebsockets:
        async def connect(self, url, **kwargs):
            if "additional_headers" in kwargs:
                raise TypeError("old websockets header name")
            verifier.verify_headers(
                headers=kwargs["extra_headers"],
                transport="websocket",
                target="/wove",
                body=b"",
            )
            captured["url"] = url
            captured["kwargs"] = kwargs
            return fake_socket

    monkeypatch.setattr("wove.environment.importlib.import_module", lambda name: FakeWebsockets())

    executor = WebSocketEnvironmentExecutor()
    await executor.start(
        environment_name="websocket",
        environment_config={
            "url": "wss://workers.internal/wove",
            "security": {"type": "signed", "secret": "secret"},
            "open_timeout": 3.0,
        },
        run_config={},
    )
    await executor.send(_run_frame("ws-run"))

    sent = fake_socket.sent[0]
    assert sent["type"] == "run_task"
    assert "callable_pickle" in sent
    assert captured["url"] == "wss://workers.internal/wove"
    assert captured["kwargs"]["extra_headers"]["X-Wove-Signature"].startswith("v1=")
    assert captured["kwargs"]["open_timeout"] == 3.0

    await fake_socket.incoming.put(
        json.dumps(
            {
                "events": [
                    {"type": "task_started", "run_id": "ws-run", "task_id": "add"},
                    {"type": "task_result", "run_id": "ws-run", "task_id": "add", "result_pickle": _pickle(13)},
                ]
            }
        )
    )
    started = await asyncio.wait_for(executor.recv(), timeout=1.0)
    result = await asyncio.wait_for(executor.recv(), timeout=1.0)
    assert started["type"] == "task_started"
    assert result["result"] == 13

    await executor.send({"type": "cancel_task", "run_id": "ws-run", "task_id": "add"})
    await executor.send({"type": "shutdown"})
    with pytest.raises(ValueError, match="Unsupported frame type"):
        await executor.send({"type": "unknown"})
    await executor.stop()
    assert fake_socket.closed is True


@pytest.mark.asyncio
async def test_websocket_executor_validation_and_missing_dependency(monkeypatch):
    executor = WebSocketEnvironmentExecutor()
    with pytest.raises(RuntimeError, match="not started"):
        await executor.recv()
    with pytest.raises(RuntimeError, match="not started"):
        await executor.send({"type": "run_task"})

    def missing(name):
        raise ImportError(name)

    monkeypatch.setattr("wove.environment.importlib.import_module", missing)
    with pytest.raises(RuntimeError, match="websocket executor requested"):
        await executor.start(environment_name="websocket", environment_config={"url": "ws://x"}, run_config={})

    class FakeWebsockets:
        async def connect(self, url, **kwargs):
            del url, kwargs
            return object()

    monkeypatch.setattr("wove.environment.importlib.import_module", lambda name: FakeWebsockets())
    with pytest.raises(TypeError, match="url"):
        await executor.start(environment_name="websocket", environment_config={}, run_config={})
    with pytest.raises(ValueError, match="ws://"):
        await executor.start(
            environment_name="websocket",
            environment_config={"url": "http://example.test/wove"},
            run_config={},
        )

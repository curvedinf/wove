import asyncio
import sys
import urllib.error
import urllib.request

import pytest

from wove import backend_worker
from wove.integrations import worker
from wove.backend import (
    BackendCallbackServer,
    build_backend_payload,
    deserialize_frame,
    payload_from_b64,
    payload_to_b64,
    run_backend_payload,
    run_backend_payload_async,
    serialize_frame,
)


def make_payload(callback_url, func, args=None, run_id="run"):
    return build_backend_payload(
        {
            "type": "run_task",
            "run_id": run_id,
            "task_id": "task",
            "task_name": "task",
            "callable": func,
            "args": args or {},
            "delivery": {"delivery_timeout": 1.0},
        },
        callback_url=callback_url,
        adapter="test",
    )


def test_frame_and_payload_serialization_round_trip():
    exc = ValueError("bad")
    payload = serialize_frame(
        {
            "type": "task_error",
            "run_id": "r",
            "task_id": "t",
            "exception": exc,
            "error": {"kind": "ValueError"},
        }
    )
    frame = deserialize_frame(payload)

    assert isinstance(frame["exception"], ValueError)
    assert frame["error"] == {"kind": "ValueError"}
    assert payload_from_b64(payload_to_b64({"x": 1})) == {"x": 1}


@pytest.mark.asyncio
async def test_callback_server_idempotent_start_public_url_and_not_started_paths():
    server = BackendCallbackServer(public_url="http://public/wove/events/token/", token="token")

    with pytest.raises(RuntimeError, match="not started"):
        await server.recv()

    await server.stop()
    await server.start()
    await server.start()

    assert server.callback_url == "http://public/wove/events/token"
    await server.stop()
    await server.stop()


@pytest.mark.asyncio
async def test_callback_server_rejects_wrong_path_and_bad_json():
    server = BackendCallbackServer(token="token")
    await server.start()
    assert server.callback_url is not None

    bad_path = server.callback_url.replace("/wove/events/token", "/wrong")
    bad_path_request = urllib.request.Request(bad_path, data=b"{}", method="POST")
    with pytest.raises(urllib.error.HTTPError) as not_found:
        await asyncio.to_thread(urllib.request.urlopen, bad_path_request)
    assert not_found.value.code == 404

    bad_json_request = urllib.request.Request(server.callback_url, data=b"not-json", method="POST")
    with pytest.raises(urllib.error.HTTPError) as bad_json:
        await asyncio.to_thread(urllib.request.urlopen, bad_json_request)
    assert bad_json.value.code == 400

    await server.stop()


@pytest.mark.asyncio
async def test_run_backend_payload_posts_error_and_cancel_frames():
    server = BackendCallbackServer()
    await server.start()
    assert server.callback_url is not None

    def boom():
        raise ValueError("broken")

    result = await run_backend_payload_async(make_payload(server.callback_url, boom, run_id="err"))
    assert result["type"] == "task_error"
    assert (await server.recv())["type"] == "task_started"
    error = await server.recv()
    assert error["type"] == "task_error"
    assert isinstance(error["exception"], ValueError)
    assert error["error"]["kind"] == "ValueError"

    async def cancelled():
        raise asyncio.CancelledError

    result = await run_backend_payload_async(make_payload(server.callback_url, cancelled, run_id="cancel"))
    assert result["type"] == "task_cancelled"
    assert (await server.recv())["type"] == "task_started"
    assert (await server.recv())["type"] == "task_cancelled"

    await server.stop()


@pytest.mark.asyncio
async def test_sync_worker_entrypoints_and_backend_worker_main(monkeypatch):
    server = BackendCallbackServer()
    await server.start()
    assert server.callback_url is not None

    payload = make_payload(server.callback_url, lambda value: value * 3, {"value": 4})
    assert await asyncio.to_thread(run_backend_payload, payload) == 12
    assert (await server.recv())["type"] == "task_started"
    assert (await server.recv())["result"] == 12

    payload = make_payload(server.callback_url, lambda: "worker-run", run_id="worker-run")
    assert await asyncio.to_thread(worker.run, payload) == "worker-run"
    assert (await server.recv())["type"] == "task_started"
    assert (await server.recv())["result"] == "worker-run"

    payload = make_payload(server.callback_url, lambda: "worker-arun", run_id="worker-arun")
    assert await worker.arun(payload) == "worker-arun"
    assert (await server.recv())["type"] == "task_started"
    assert (await server.recv())["result"] == "worker-arun"

    payload = make_payload(server.callback_url, lambda: "main", run_id="main")
    monkeypatch.setattr(sys, "argv", ["wove.backend_worker", payload_to_b64(payload)])
    assert await asyncio.to_thread(backend_worker.main) == 0
    assert (await server.recv())["type"] == "task_started"
    assert (await server.recv())["result"] == "main"

    payload = make_payload(server.callback_url, lambda: "env", run_id="env")
    monkeypatch.setattr(sys, "argv", ["wove.backend_worker"])
    monkeypatch.setenv("WOVE_BACKEND_PAYLOAD", payload_to_b64(payload))
    assert await asyncio.to_thread(backend_worker.main) == 0
    assert (await server.recv())["type"] == "task_started"
    assert (await server.recv())["result"] == "env"

    monkeypatch.setattr(sys, "argv", ["wove.backend_worker"])
    monkeypatch.delenv("WOVE_BACKEND_PAYLOAD", raising=False)
    with pytest.raises(SystemExit, match="Missing dispatch payload"):
        backend_worker.main()

    with pytest.raises(RuntimeError, match="already inside an event loop"):
        run_backend_payload(payload)

    await server.stop()

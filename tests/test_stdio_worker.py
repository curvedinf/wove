import asyncio
import base64
import json
from argparse import Namespace
from contextlib import suppress

import cloudpickle
import pytest

from wove import stdio_worker
from wove.stdio_worker import StdioWorkerRuntime


class _LoopFeeder:
    def __init__(self, payloads):
        self._payloads = list(payloads)

    async def run_in_executor(self, _executor, _fn):
        if not self._payloads:
            return b""
        return self._payloads.pop(0)


@pytest.mark.asyncio
async def test_stdio_worker_run_handles_invalid_unknown_and_shutdown(monkeypatch):
    frames = []
    rt = StdioWorkerRuntime(adapter="custom")

    async def capture_emit(frame):
        frames.append(frame)

    monkeypatch.setattr(rt, "_emit", capture_emit)

    payloads = [
        b"not-json\n",
        json.dumps({"type": "unknown"}).encode("utf-8") + b"\n",
        json.dumps({"type": "shutdown"}).encode("utf-8") + b"\n",
    ]
    monkeypatch.setattr(stdio_worker.asyncio, "get_running_loop", lambda: _LoopFeeder(payloads))

    await rt.run()

    assert any(frame.get("type") == "log" and "Invalid stdio worker frame" in frame.get("message", "") for frame in frames)
    assert any(frame.get("type") == "log" and "Unknown frame type" in frame.get("message", "") for frame in frames)


@pytest.mark.asyncio
async def test_stdio_worker_run_cleans_up_active_tasks(monkeypatch):
    rt = StdioWorkerRuntime()
    blocker = asyncio.Event()

    async def blocked():
        await blocker.wait()

    active_task = asyncio.create_task(blocked())
    rt._active["r1"] = active_task

    monkeypatch.setattr(stdio_worker.asyncio, "get_running_loop", lambda: _LoopFeeder([b""]))

    await rt.run()
    assert active_task.cancelled()
    assert rt._active == {}


@pytest.mark.asyncio
async def test_handle_run_task_emits_result_and_unpickles_args(monkeypatch):
    emitted = []
    rt = StdioWorkerRuntime()

    async def capture_emit(frame):
        emitted.append(frame)

    monkeypatch.setattr(rt, "_emit", capture_emit)

    def add(a, b):
        return a + b

    frame = {
        "run_id": "run-1",
        "task_id": "task-1",
        "callable_pickle": base64.b64encode(cloudpickle.dumps(add)).decode("ascii"),
        "args_pickle": base64.b64encode(cloudpickle.dumps({"a": 2, "b": 3})).decode("ascii"),
        "delivery": {},
    }

    await rt._handle_run_task(frame)
    worker = rt._active["run-1"]
    await worker

    started = [f for f in emitted if f.get("type") == "task_started"]
    results = [f for f in emitted if f.get("type") == "task_result"]
    assert started and results
    assert cloudpickle.loads(base64.b64decode(results[0]["result_pickle"])) == 5


@pytest.mark.asyncio
async def test_execute_task_emits_error_payload(monkeypatch):
    emitted = []
    rt = StdioWorkerRuntime(adapter="ray")

    async def capture_emit(frame):
        emitted.append(frame)

    monkeypatch.setattr(rt, "_emit", capture_emit)

    def boom():
        raise ValueError("explode")

    await rt._execute_task(
        run_id="run-err",
        task_id="task-err",
        task_callable=boom,
        task_args={},
        delivery={},
    )

    err = next(frame for frame in emitted if frame.get("type") == "task_error")
    payload = cloudpickle.loads(base64.b64decode(err["error_pickle"]))
    exc = cloudpickle.loads(base64.b64decode(err["exception_pickle"]))
    assert payload["kind"] == "ValueError"
    assert payload["adapter"] == "ray"
    assert str(exc) == "explode"


@pytest.mark.asyncio
async def test_execute_task_emits_heartbeat_and_handles_cancellation(monkeypatch):
    emitted = []
    rt = StdioWorkerRuntime()

    async def capture_emit(frame):
        emitted.append(frame)

    monkeypatch.setattr(rt, "_emit", capture_emit)

    async def slow():
        await asyncio.sleep(0.03)
        return "ok"

    await rt._execute_task(
        run_id="run-heartbeat",
        task_id="task-heartbeat",
        task_callable=slow,
        task_args={},
        delivery={"delivery_heartbeat_seconds": 0.01},
    )

    assert any(frame.get("type") == "heartbeat" for frame in emitted)

    emitted.clear()
    pending = asyncio.create_task(
        rt._execute_task(
            run_id="run-cancel",
            task_id="task-cancel",
            task_callable=slow,
            task_args={},
            delivery={"delivery_heartbeat_seconds": 0.01},
        )
    )
    await asyncio.sleep(0.005)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending

    assert any(frame.get("type") == "task_cancelled" for frame in emitted)


@pytest.mark.asyncio
async def test_cancel_and_shutdown_handlers_cancel_active_tasks():
    rt = StdioWorkerRuntime()
    blocker = asyncio.Event()

    async def blocked():
        await blocker.wait()

    task = asyncio.create_task(blocked())
    rt._active["run-1"] = task

    await rt._handle_cancel_task({})
    assert not task.cancelled()

    await rt._handle_cancel_task({"run_id": "run-1"})
    await asyncio.sleep(0)
    assert task.cancelled()

    second = asyncio.create_task(blocked())
    rt._active["run-2"] = second
    await rt._handle_shutdown({"delivery_orphan_policy": "detach"})
    await asyncio.sleep(0)
    assert rt._stopping is True
    assert second.cancelled()


@pytest.mark.asyncio
async def test_emit_writes_json_line(monkeypatch):
    written = []

    class _Stdout:
        def write(self, data):
            written.append(data)

        def flush(self):
            written.append("<flushed>")

    rt = StdioWorkerRuntime()
    monkeypatch.setattr(stdio_worker.sys, "stdout", _Stdout())

    await rt._emit({"type": "log", "message": "ok"})
    assert written[0].endswith("\n")
    assert '"type":"log"' in written[0]
    assert written[1] == "<flushed>"


def test_main_builds_runtime_and_runs(monkeypatch):
    captured = {}

    class _FakeStdioWorker:
        def __init__(self, *, adapter):
            captured["adapter"] = adapter

        async def run(self):
            captured["run_called"] = True

    def fake_asyncio_run(coro):
        captured["asyncio_run_called"] = True
        with suppress(Exception):
            coro.close()

    monkeypatch.setattr(stdio_worker, "StdioWorkerRuntime", _FakeStdioWorker)
    monkeypatch.setattr(stdio_worker.asyncio, "run", fake_asyncio_run)
    monkeypatch.setattr(stdio_worker.argparse.ArgumentParser, "parse_args", lambda self: Namespace(adapter="temporal"))

    stdio_worker.main()

    assert captured["adapter"] == "temporal"
    assert captured["asyncio_run_called"] is True

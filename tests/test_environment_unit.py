import asyncio
from contextlib import suppress

import pytest

from wove.environment import (
    BackendAdapterEnvironmentExecutor,
    DeliveryOrphanedError,
    EnvironmentExecutionError,
    EnvironmentExecutor,
    ExecutorRuntime,
    LocalEnvironmentExecutor,
    StdioEnvironmentExecutor,
    build_executor_from_name,
    coerce_executor,
    normalize_exception,
)
from wove.backend import BackendCallbackServer, build_backend_payload, post_event, run_backend_payload_async


class QueueExecutor(EnvironmentExecutor):
    def __init__(self):
        self.sent = []
        self.events = asyncio.Queue()
        self.fail_send = False

    async def start(self, *, environment_name, environment_config, run_config):
        del environment_name, environment_config, run_config

    async def send(self, frame):
        self.sent.append(frame)
        if self.fail_send:
            raise RuntimeError("send failed")

    async def recv(self):
        return await self.events.get()

    async def stop(self):
        return None


@pytest.mark.asyncio
async def test_local_executor_success_error_cancel_and_shutdown():
    ex = LocalEnvironmentExecutor()
    await ex.start(environment_name="local", environment_config={}, run_config={})

    await ex.send({
        "type": "run_task",
        "run_id": "ok",
        "task_id": "ok",
        "callable": lambda: 1,
        "args": {},
    })
    assert (await ex.recv())["type"] == "task_started"
    assert (await ex.recv())["type"] == "task_result"

    def boom():
        raise ValueError("boom")

    await ex.send({
        "type": "run_task",
        "run_id": "err",
        "task_id": "err",
        "callable": boom,
        "args": {},
    })
    assert (await ex.recv())["type"] == "task_started"
    err = await ex.recv()
    assert err["type"] == "task_error"
    assert err["error"]["kind"] == "ValueError"

    async def slow():
        await asyncio.sleep(1)

    await ex.send({
        "type": "run_task",
        "run_id": "cancel",
        "task_id": "cancel",
        "callable": slow,
        "args": {},
    })
    assert (await ex.recv())["type"] == "task_started"
    await ex.send({"type": "cancel_task", "run_id": "cancel"})
    assert (await ex.recv())["type"] == "task_cancelled"

    await ex.send({"type": "shutdown"})

    with pytest.raises(ValueError, match="Unsupported frame type"):
        await ex.send({"type": "unknown"})

    await ex.stop()


def test_environment_error_and_normalize_exception_helpers():
    err = EnvironmentExecutionError({"message": "failed", "kind": "x"})
    assert str(err) == "failed"
    payload = normalize_exception(ValueError("boom"), source="transport", retryable=True)
    assert payload["kind"] == "ValueError"
    assert payload["retryable"] is True
    assert payload["source"] == "transport"


@pytest.mark.asyncio
async def test_stdio_send_recv_and_not_started_errors():
    ex = StdioEnvironmentExecutor()

    with pytest.raises(RuntimeError, match="not started"):
        await ex.send({"type": "run_task"})

    with pytest.raises(RuntimeError, match="not started"):
        await ex.recv()

    with pytest.raises(TypeError, match="executor_config.command"):
        await ex.start(environment_name="s", environment_config={"command": 123}, run_config={})

    await ex.start(
        environment_name="s",
        environment_config={"command": f"{__import__('sys').executable} -m wove.stdio_worker"},
        run_config={},
    )

    run_frame = {
        "type": "run_task",
        "run_id": "s1",
        "task_id": "task",
        "callable": lambda a: a + 1,
        "args": {"a": 2},
        "delivery": {},
    }
    await ex.send(run_frame)
    started = await ex.recv()
    result = await ex.recv()
    assert started["type"] == "task_started"
    assert result["type"] == "task_result"
    assert result["result"] == 3

    # Also cover exception/error pickle decode branches
    await ex.send(
        {
            "type": "run_task",
            "run_id": "s2",
            "task_id": "task2",
            "callable": lambda: (_ for _ in ()).throw(ValueError("x")),
            "args": {},
            "delivery": {},
        }
    )
    _ = await ex.recv()
    err = await ex.recv()
    assert err["type"] == "task_error"
    assert isinstance(err["exception"], ValueError)
    assert isinstance(err["error"], dict)

    await ex.stop()


@pytest.mark.asyncio
async def test_backend_callback_server_receives_frames():
    server = BackendCallbackServer()
    await server.start()
    assert server.callback_url is not None

    await asyncio.to_thread(
        post_event,
        server.callback_url,
        {"type": "task_result", "run_id": "r1", "task_id": "t1", "result": {"ok": True}},
    )
    frame = await asyncio.wait_for(server.recv(), timeout=1.0)

    assert frame["type"] == "task_result"
    assert frame["result"] == {"ok": True}
    await server.stop()


@pytest.mark.asyncio
async def test_run_backend_payload_posts_started_and_result():
    server = BackendCallbackServer()
    await server.start()
    assert server.callback_url is not None

    payload = build_backend_payload(
        {
            "type": "run_task",
            "run_id": "r2",
            "task_id": "t2",
            "callable": lambda value: value + 4,
            "args": {"value": 5},
        },
        callback_url=server.callback_url,
        adapter="test",
    )

    result = await run_backend_payload_async(payload)
    started = await asyncio.wait_for(server.recv(), timeout=1.0)
    finished = await asyncio.wait_for(server.recv(), timeout=1.0)

    assert result == 9
    assert started["type"] == "task_started"
    assert finished["type"] == "task_result"
    assert finished["result"] == 9
    await server.stop()


@pytest.mark.asyncio
async def test_stdio_recv_eof_and_stop_paths(monkeypatch):
    ex = StdioEnvironmentExecutor()

    class _Stdout:
        async def readline(self):
            return b""

    class _Proc:
        returncode = None

        class _In:
            def write(self, _d):
                return None

            async def drain(self):
                return None

        stdin = _In()
        stdout = _Stdout()

        def terminate(self):
            self.terminated = True

        async def wait(self):
            return None

    ex._process = _Proc()

    with pytest.raises(RuntimeError, match="closed stdout"):
        await ex.recv()

    # send() failure in stop() is swallowed
    ex._process.stdin = None
    await ex.stop()

    # timeout path in stop() triggers terminate + wait
    ex._process = _Proc()
    terminated = {"called": False}

    def mark_terminate():
        terminated["called"] = True

    ex._process.terminate = mark_terminate

    async def fake_wait_for(_awaitable, timeout):
        del timeout
        close = getattr(_awaitable, "close", None)
        if callable(close):
            close()
        raise asyncio.TimeoutError

    monkeypatch.setattr("wove.environment.asyncio.wait_for", fake_wait_for)
    await ex.stop()
    assert terminated["called"] is True


@pytest.mark.asyncio
async def test_backend_adapter_executor_not_started_paths():
    ex = BackendAdapterEnvironmentExecutor("celery", required_modules=("celery",))
    with pytest.raises(RuntimeError, match="not started"):
        await ex.send({"type": "run_task"})
    with pytest.raises(RuntimeError, match="not started"):
        await ex.recv()
    await ex.stop()


def test_build_and_coerce_executor_errors():
    with pytest.raises(ValueError, match="Unknown executor"):
        build_executor_from_name("unknown")
    with pytest.raises(TypeError, match="must be a string"):
        coerce_executor(123)


@pytest.mark.asyncio
async def test_executor_runtime_recv_task_done_branches_and_invalid_cancel_mode():
    rt = ExecutorRuntime({}, {})
    rt._executors["e"] = LocalEnvironmentExecutor()
    rt._pending["e"] = {}
    rt._run_metadata["e"] = {}

    cancelled_task = asyncio.create_task(asyncio.sleep(0.01))
    cancelled_task.cancel()
    with suppress(asyncio.CancelledError):
        await cancelled_task
    rt._recv_tasks["e"] = cancelled_task
    with pytest.raises(RuntimeError, match="was cancelled"):
        await rt.run_task(
            task_name="a",
            task_func=lambda: 1,
            task_args={},
            task_info={"environment": "e"},
        )

    async def explode():
        raise RuntimeError("rx failed")

    failed_task = asyncio.create_task(explode())
    with suppress(RuntimeError):
        await failed_task
    rt._recv_tasks["e"] = failed_task
    with pytest.raises(RuntimeError, match="stopped unexpectedly"):
        await rt.run_task(
            task_name="a",
            task_func=lambda: 1,
            task_args={},
            task_info={"environment": "e"},
        )

    done_task = asyncio.create_task(asyncio.sleep(0))
    await done_task
    rt._recv_tasks["e"] = done_task
    with pytest.raises(RuntimeError, match="is not running"):
        await rt.run_task(
            task_name="a",
            task_func=lambda: 1,
            task_args={},
            task_info={"environment": "e"},
        )

    # Unknown environment
    with pytest.raises(NameError, match="unknown environment"):
        await rt.run_task(
            task_name="a",
            task_func=lambda: 1,
            task_args={},
            task_info={"environment": "missing"},
        )

    running_recv = asyncio.create_task(asyncio.sleep(3600))
    rt._recv_tasks["e"] = running_recv
    with pytest.raises(ValueError, match="delivery_cancel_mode"):
        await rt.run_task(
            task_name="a",
            task_func=lambda: 1,
            task_args={},
            task_info={"environment": "e", "delivery_cancel_mode": "bad"},
        )
    running_recv.cancel()
    with suppress(asyncio.CancelledError):
        await running_recv


@pytest.mark.asyncio
async def test_executor_runtime_run_task_with_inflight_semaphore():
    ex = QueueExecutor()
    rt = ExecutorRuntime({"e": {"executor": ex}}, {})
    await rt.start()

    async def enqueue_result(run_id):
        await ex.events.put({"type": "task_result", "run_id": run_id, "task_id": "task", "result": 9})

    async def send_and_ack(frame):
        ex.sent.append(frame)
        if frame["type"] == "run_task":
            await enqueue_result(frame["run_id"])

    ex.send = send_and_ack  # type: ignore[assignment]

    result = await rt.run_task(
        task_name="task",
        task_func=lambda: 9,
        task_args={},
        task_info={"environment": "e", "delivery_max_in_flight": 1},
    )
    assert result == 9
    assert ("e", 1) in rt._inflight_semaphores

    await rt.stop()


@pytest.mark.asyncio
async def test_executor_runtime_helper_methods_and_recv_loop_paths():
    ex = QueueExecutor()
    rt = ExecutorRuntime({"e": {"executor": ex}}, {"delivery_orphan_policy": "cancel"})

    # Direct helper coverage
    assert rt._resolve_orphan_policy("e", {}) == "cancel"
    with pytest.raises(ValueError, match="delivery_orphan_policy"):
        rt._resolve_orphan_policy("e", {"delivery_orphan_policy": "bad"})

    sem_a = rt._resolve_inflight_semaphore("e", 2)
    sem_b = rt._resolve_inflight_semaphore("e", 2)
    assert sem_a is sem_b
    assert rt._resolve_inflight_semaphore("e", 0) is None

    assert rt._resolve_delivery_idempotency_key({"delivery_idempotency_key": lambda args: args["x"]}, {"x": 1}, "t") == "1"

    def key_factory(**kwargs):
        return kwargs["x"]

    assert rt._resolve_delivery_idempotency_key({"delivery_idempotency_key": key_factory}, {"x": 2}, "t") == "2"
    assert rt._resolve_delivery_idempotency_key({"delivery_idempotency_key": "k:{missing}"}, {"x": 1}, "t") == "k:{missing}"
    assert rt._resolve_delivery_idempotency_key({"delivery_idempotency_key": 123}, {}, "t") == "123"

    assert rt.is_local_environment("missing") is True
    rt._environment_definitions["z"] = {"executor": LocalEnvironmentExecutor()}
    assert rt.is_local_environment("z") is True

    # _exception_from_error_frame branches
    e = ValueError("x")
    assert rt._exception_from_error_frame({"exception": e}) is e
    coerced = rt._exception_from_error_frame({"error": "bad"})
    assert isinstance(coerced, EnvironmentExecutionError)

    # _await_result immediate done and cancellation branch
    done_future = asyncio.get_running_loop().create_future()
    done_future.set_result("ok")
    assert await rt._await_result(
        environment_name="e",
        run_id="r",
        future=done_future,
        executor=ex,
        cancel_frame={"type": "cancel_task"},
        delivery_timeout=None,
        heartbeat_seconds=None,
        task_name="t",
    ) == "ok"

    pending_future = asyncio.get_running_loop().create_future()

    waiter = asyncio.create_task(
        rt._await_result(
            environment_name="e",
            run_id="r2",
            future=pending_future,
            executor=ex,
            cancel_frame={"type": "cancel_task", "run_id": "r2"},
            delivery_timeout=None,
            heartbeat_seconds=None,
            task_name="t2",
        )
    )
    await asyncio.sleep(0)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter

    assert any(frame.get("type") == "cancel_task" for frame in ex.sent)


@pytest.mark.asyncio
async def test_recv_loop_frame_types_and_receiver_failure_orphan_handling():
    ex = QueueExecutor()
    rt = ExecutorRuntime({}, {})
    rt._pending["e"] = {}
    rt._run_metadata["e"] = {}

    loop_task = asyncio.create_task(rt._recv_loop("e", ex))

    f_cancel = asyncio.get_running_loop().create_future()
    f_unknown = asyncio.get_running_loop().create_future()
    rt._pending["e"]["r1"] = f_cancel
    rt._pending["e"]["r2"] = f_unknown
    rt._run_metadata["e"]["r1"] = {"task_id": "t1", "delivery_orphan_policy": "cancel"}
    rt._run_metadata["e"]["r2"] = {"task_id": "t2", "delivery_orphan_policy": "cancel"}

    await ex.events.put({"type": "heartbeat", "run_id": "r1"})
    await ex.events.put({"type": "log", "run_id": "r1"})
    await ex.events.put({"type": "task_cancelled", "run_id": "r1"})
    await ex.events.put({"type": "unknown", "run_id": "r2"})
    await ex.events.put({"type": "task_started"})

    with pytest.raises(asyncio.CancelledError):
        await f_cancel
    with pytest.raises(RuntimeError, match="Unknown executor frame type"):
        await f_unknown

    loop_task.cancel()
    with suppress(asyncio.CancelledError):
        await loop_task

    # Receiver failure branch with orphan policy != cancel
    class CrashingExecutor(EnvironmentExecutor):
        async def start(self, *, environment_name, environment_config, run_config):
            del environment_name, environment_config, run_config

        async def send(self, frame):
            del frame

        async def recv(self):
            raise RuntimeError("boom")

        async def stop(self):
            return None

    crash = CrashingExecutor()
    rt2 = ExecutorRuntime({}, {})
    rt2._pending["e"] = {
        "r1": asyncio.get_running_loop().create_future(),
        "r2": asyncio.get_running_loop().create_future(),
    }
    rt2._run_metadata["e"] = {
        "r1": {"task_id": "t1", "delivery_orphan_policy": "cancel"},
        "r2": {"task_id": "t2", "delivery_orphan_policy": "requeue"},
    }

    with pytest.raises(RuntimeError, match="boom"):
        await rt2._recv_loop("e", crash)

    assert isinstance(rt2._pending["e"]["r1"].exception(), RuntimeError)
    assert isinstance(rt2._pending["e"]["r2"].exception(), DeliveryOrphanedError)


@pytest.mark.asyncio
async def test_orphan_pending_futures_branches_and_runtime_stop_sets_cancelled():
    ex = QueueExecutor()
    rt = ExecutorRuntime({"e": {"executor": ex}}, {})
    rt._executors["e"] = ex
    rt._pending["e"] = {}
    rt._run_metadata["e"] = {}
    rt._recv_tasks["e"] = asyncio.create_task(asyncio.sleep(3600))

    done_future = asyncio.get_running_loop().create_future()
    done_future.set_result("done")
    cancel_future = asyncio.get_running_loop().create_future()
    requeue_future = asyncio.get_running_loop().create_future()

    rt._pending["e"]["done"] = done_future
    rt._run_metadata["e"]["done"] = {"task_id": "done", "delivery_orphan_policy": "cancel"}

    rt._pending["e"]["cancel"] = cancel_future
    rt._run_metadata["e"]["cancel"] = {
        "task_id": "cancel",
        "delivery_orphan_policy": "cancel",
        "delivery_cancel_mode": "best_effort",
    }

    rt._pending["e"]["requeue"] = requeue_future
    rt._run_metadata["e"]["requeue"] = {
        "task_id": "requeue",
        "delivery_orphan_policy": "requeue",
        "delivery_cancel_mode": "best_effort",
    }

    ex.fail_send = True  # cover swallowed send failure in orphan handler
    await rt._orphan_pending_futures()

    assert cancel_future.done()
    with pytest.raises(asyncio.CancelledError):
        cancel_future.result()

    assert isinstance(requeue_future.exception(), DeliveryOrphanedError)

    # stop() should still complete and clear state
    await rt.stop()
    assert rt._executors == {}
    assert rt._pending == {}

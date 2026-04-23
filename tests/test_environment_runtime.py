import copy
import asyncio

import pytest

from wove import config, weave
from wove.environment import (
    DeliveryOrphanedError,
    DeliveryTimeoutError,
    EnvironmentExecutor,
    ExecutorRuntime,
    RemoteAdapterEnvironmentExecutor,
)
from wove.integrations.base import RemoteTaskAdapter
from wove.remote import run_remote_payload_async
from wove.runtime import runtime


@pytest.fixture
def restore_runtime():
    snapshot = runtime.snapshot()
    yield
    runtime.default_environment = snapshot["default_environment"]
    runtime.environments = copy.deepcopy(snapshot["environments"])
    runtime.global_defaults = {
        key: value
        for key, value in snapshot.items()
        if key not in {"default_environment", "environments"}
    }


def test_unknown_weave_environment_raises(restore_runtime):
    with pytest.raises(NameError, match="not configured"):
        weave(environment="missing")


@pytest.mark.asyncio
async def test_local_environment_executor_runs(restore_runtime):
    config(
        default_environment="default",
        environments={"default": {"executor": "local"}},
    )

    async with weave(environment="default") as w:
        @w.do
        async def a():
            return 1

    assert w.result.a == 1


@pytest.mark.asyncio
async def test_optional_adapter_missing_dependency_fails_fast(restore_runtime, monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    config(
        default_environment="celery_env",
        environments={
            "celery_env": {
                "executor": "celery",
                "executor_config": {"command": ["python", "-m", "fake_gateway"]},
            }
        },
    )

    with pytest.raises(RuntimeError, match="celery executor requested"):
        async with weave() as w:
            @w.do
            async def task():
                return 1


@pytest.mark.asyncio
async def test_remote_adapter_uses_callback_delivery(restore_runtime):
    class InlineRemoteAdapter(RemoteTaskAdapter):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.tasks = []

        async def submit(self, payload, frame):
            del frame
            task = asyncio.create_task(run_remote_payload_async(payload))
            self.tasks.append(task)
            return task

        async def close(self):
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)

    executor = RemoteAdapterEnvironmentExecutor(
        "inline",
        adapter_class=InlineRemoteAdapter,
        required_modules=(),
    )
    config(
        default_environment="remote",
        environments={
            "remote": {
                "executor": executor,
                "executor_config": {},
            }
        },
    )

    async with weave() as w:
        @w.do
        async def task():
            return 3

    assert w.result.task == 3


@pytest.mark.asyncio
async def test_recv_loop_failure_propagates_to_pending_tasks(restore_runtime):
    class CrashingExecutor(EnvironmentExecutor):
        def __init__(self):
            self._run_sent = asyncio.Event()

        async def start(self, *, environment_name, environment_config, run_config):
            del environment_name, environment_config, run_config

        async def send(self, frame):
            if frame.get("type") == "run_task":
                self._run_sent.set()

        async def recv(self):
            await self._run_sent.wait()
            raise RuntimeError("gateway crashed")

        async def stop(self):
            return None

    config(
        default_environment="crash",
        environments={"crash": {"executor": CrashingExecutor()}},
    )

    async with weave() as w:
        @w.do
        async def task():
            return 1

    assert isinstance(w.result.exception, RuntimeError)
    assert "gateway crashed" in str(w.result.exception)
    assert any("gateway crashed" in str(err) for err in w.result._errors.values())


@pytest.mark.asyncio
async def test_remote_environment_receives_raw_sync_callable(restore_runtime):
    class CaptureExecutor(EnvironmentExecutor):
        def __init__(self):
            self._events = asyncio.Queue()
            self.received_callable = None

        async def start(self, *, environment_name, environment_config, run_config):
            del environment_name, environment_config, run_config

        async def send(self, frame):
            if frame["type"] != "run_task":
                return
            self.received_callable = frame["callable"]
            value = frame["callable"](**frame["args"])
            if asyncio.iscoroutine(value):
                value = await value
            await self._events.put(
                {
                    "type": "task_result",
                    "run_id": frame["run_id"],
                    "task_id": frame["task_id"],
                    "result": value,
                }
            )

        async def recv(self):
            return await self._events.get()

        async def stop(self):
            return None

    capture = CaptureExecutor()
    config(
        default_environment="remote",
        environments={"remote": {"executor": capture}},
    )

    async with weave() as w:
        @w.do
        def sync_task():
            return 7

    assert w.result.sync_task == 7
    assert capture.received_callable is not None
    assert not asyncio.iscoroutinefunction(capture.received_callable)


@pytest.mark.asyncio
async def test_delivery_prefixed_options_are_forwarded(restore_runtime):
    class CaptureDeliveryExecutor(EnvironmentExecutor):
        def __init__(self):
            self._events = asyncio.Queue()
            self.received_frame = None

        async def start(self, *, environment_name, environment_config, run_config):
            del environment_name, environment_config, run_config

        async def send(self, frame):
            if frame["type"] != "run_task":
                return
            self.received_frame = frame
            value = frame["callable"](**frame["args"])
            if asyncio.iscoroutine(value):
                value = await value
            await self._events.put(
                {
                    "type": "task_result",
                    "run_id": frame["run_id"],
                    "task_id": frame["task_id"],
                    "result": value,
                }
            )

        async def recv(self):
            return await self._events.get()

        async def stop(self):
            return None

    capture = CaptureDeliveryExecutor()
    config(
        default_environment="remote",
        environments={
            "remote": {
                "executor": capture,
                "delivery_timeout": 7.5,
                "delivery_cancel_mode": "require_ack",
                "delivery_orphan_policy": "requeue",
            }
        },
    )

    async with weave(value=2) as w:
        @w.do(delivery_idempotency_key="job:{value}")
        def task(value):
            return value * 2

    assert w.result.task == 4
    assert capture.received_frame is not None
    delivery = capture.received_frame["delivery"]
    assert delivery["delivery_timeout"] == 7.5
    assert delivery["delivery_cancel_mode"] == "require_ack"
    assert delivery["delivery_orphan_policy"] == "requeue"
    assert delivery["delivery_idempotency_key"] == "job:2"


@pytest.mark.asyncio
async def test_delivery_timeout_cancels_remote_attempt(restore_runtime):
    class SlowAckExecutor(EnvironmentExecutor):
        def __init__(self):
            self.frames = []
            self.events = asyncio.Queue()

        async def start(self, *, environment_name, environment_config, run_config):
            del environment_name, environment_config, run_config

        async def send(self, frame):
            self.frames.append(frame)
            if frame.get("type") == "run_task":
                async def delayed_result():
                    await asyncio.sleep(0.2)
                    await self.events.put(
                        {
                            "type": "task_result",
                            "run_id": frame["run_id"],
                            "task_id": frame["task_id"],
                            "result": 1,
                        }
                    )

                asyncio.create_task(delayed_result())

        async def recv(self):
            return await self.events.get()

        async def stop(self):
            return None

    silent = SlowAckExecutor()
    config(
        default_environment="remote",
        environments={
            "remote": {
                "executor": silent,
                "delivery_timeout": 0.01,
            }
        },
    )

    async with weave() as w:
        @w.do
        async def task():
            return 1

    with pytest.raises(DeliveryTimeoutError, match="Delivery timeout exceeded"):
        _ = w.result.task
    assert any(frame.get("type") == "cancel_task" for frame in silent.frames)


@pytest.mark.asyncio
async def test_stdio_executor_uses_default_gateway_command(restore_runtime):
    config(
        default_environment="stdio_env",
        environments={"stdio_env": {"executor": "stdio"}},
    )

    async with weave() as w:
        @w.do
        def answer():
            return 42

    assert w.result.answer == 42


@pytest.mark.asyncio
async def test_delivery_heartbeat_timeout_cancels_remote_attempt(restore_runtime):
    class SilentExecutor(EnvironmentExecutor):
        def __init__(self):
            self.frames = []
            self.events = asyncio.Queue()

        async def start(self, *, environment_name, environment_config, run_config):
            del environment_name, environment_config, run_config

        async def send(self, frame):
            self.frames.append(frame)
            if frame.get("type") == "run_task":
                await self.events.put(
                    {
                        "type": "task_started",
                        "run_id": frame["run_id"],
                        "task_id": frame["task_id"],
                    }
                )
                async def delayed_result():
                    await asyncio.sleep(0.1)
                    await self.events.put(
                        {
                            "type": "task_result",
                            "run_id": frame["run_id"],
                            "task_id": frame["task_id"],
                            "result": 1,
                        }
                    )

                asyncio.create_task(delayed_result())

        async def recv(self):
            return await self.events.get()

        async def stop(self):
            return None

    silent = SilentExecutor()
    config(
        default_environment="remote",
        environments={
            "remote": {
                "executor": silent,
                "delivery_heartbeat_seconds": 0.02,
            }
        },
    )

    async with weave() as w:
        @w.do
        async def task():
            return 1

    with pytest.raises(DeliveryTimeoutError, match="heartbeat"):
        _ = w.result.task
    assert any(frame.get("type") == "cancel_task" for frame in silent.frames)


@pytest.mark.asyncio
async def test_delivery_orphan_policy_requeue_marks_pending_as_orphaned():
    class IdleExecutor(EnvironmentExecutor):
        def __init__(self):
            self.frames = []

        async def start(self, *, environment_name, environment_config, run_config):
            del environment_name, environment_config, run_config

        async def send(self, frame):
            self.frames.append(frame)

        async def recv(self):
            await asyncio.sleep(3600)
            return {}

        async def stop(self):
            return None

    idle = IdleExecutor()
    runtime_exec = ExecutorRuntime(
        environment_definitions={
            "remote": {
                "executor": idle,
                "delivery_orphan_policy": "requeue",
            }
        },
        run_config={},
    )
    await runtime_exec.start()

    loop = asyncio.get_running_loop()
    pending = loop.create_future()
    runtime_exec._pending["remote"]["run-1"] = pending
    runtime_exec._run_metadata["remote"]["run-1"] = {
        "task_id": "task_a",
        "delivery_cancel_mode": "best_effort",
        "delivery_orphan_policy": "requeue",
    }

    await runtime_exec.stop()

    assert pending.done()
    assert isinstance(pending.exception(), DeliveryOrphanedError)
    assert any(
        frame.get("type") == "cancel_task" and frame.get("delivery_orphan_policy") == "requeue"
        for frame in idle.frames
    )

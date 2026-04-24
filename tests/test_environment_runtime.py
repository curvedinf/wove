import copy
import asyncio
import importlib
import os
import sys
from pathlib import Path

import pytest

from wove import config, weave
from wove.environment import (
    BackendAdapterEnvironmentExecutor,
    DeliveryOrphanedError,
    DeliveryTimeoutError,
    EnvironmentExecutor,
    ExecutorRuntime,
)
from wove.integrations.base import BackendAdapter
from wove.backend import run_backend_payload_async
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


class InlineRemoteExecutor(EnvironmentExecutor):
    def __init__(self):
        self.events = asyncio.Queue()
        self.frames = []
        self.tasks = []
        self.environment_name = None
        self.environment_config = None
        self.run_config = None

    async def start(self, *, environment_name, environment_config, run_config):
        self.environment_name = environment_name
        self.environment_config = environment_config
        self.run_config = run_config

    async def send(self, frame):
        self.frames.append(frame)
        if frame.get("type") != "run_task":
            return
        task = asyncio.create_task(self._run_frame(frame))
        self.tasks.append(task)

    async def recv(self):
        return await self.events.get()

    async def stop(self):
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

    async def _run_frame(self, frame):
        await self.events.put(
            {
                "type": "task_started",
                "run_id": frame["run_id"],
                "task_id": frame["task_id"],
            }
        )
        try:
            value = frame["callable"](**frame["args"])
            if asyncio.iscoroutine(value):
                value = await value
        except Exception as exc:
            await self.events.put(
                {
                    "type": "task_error",
                    "run_id": frame["run_id"],
                    "task_id": frame["task_id"],
                    "exception": exc,
                }
            )
            return
        await self.events.put(
            {
                "type": "task_result",
                "run_id": frame["run_id"],
                "task_id": frame["task_id"],
                "result": value,
            }
        )


class InlineBackendAdapter(BackendAdapter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submissions = []

    async def submit(self, payload, frame):
        self.submissions.append((payload, frame))
        task = asyncio.create_task(run_backend_payload_async(payload))
        return task


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
async def test_remote_environment_task_reintegrates_into_local_weave(restore_runtime):
    remote = InlineRemoteExecutor()
    config(
        default_environment="local",
        environments={
            "local": {"executor": "local"},
            "remote": {"executor": remote, "executor_config": {"region": "test"}},
        },
    )

    async with weave(environment="local", seed=4) as w:
        @w.do
        def local_input(seed):
            return seed + 1

        @w.do(environment="remote")
        def remote_profile(local_input):
            return {"id": local_input, "score": local_input * 10}

        @w.do
        async def local_flags(local_input):
            await asyncio.sleep(0)
            return ["vip"] if local_input > 3 else []

        @w.do
        def response(remote_profile, local_flags):
            return {
                "id": remote_profile["id"],
                "score": remote_profile["score"],
                "flags": local_flags,
            }

    assert w.result.response == {"id": 5, "score": 50, "flags": ["vip"]}
    assert remote.environment_name == "remote"
    assert remote.environment_config == {"region": "test"}

    run_frames = [frame for frame in remote.frames if frame.get("type") == "run_task"]
    assert len(run_frames) == 1
    assert run_frames[0]["task_id"] == "remote_profile"
    assert run_frames[0]["args"] == {"local_input": 5}


@pytest.mark.asyncio
async def test_mapped_remote_environment_task_reintegrates_list_result(restore_runtime):
    remote = InlineRemoteExecutor()
    config(
        default_environment="local",
        environments={
            "local": {"executor": "local"},
            "remote": {"executor": remote},
        },
    )

    async with weave(environment="local") as w:
        @w.do
        def customer_ids():
            return [3, 4, 5]

        @w.do("customer_ids", workers=2, environment="remote")
        def enrichment(item):
            return {"customer_id": item, "score": item * 100}

        @w.do
        def score_total(enrichment):
            return sum(row["score"] for row in enrichment)

    assert w.result.enrichment == [
        {"customer_id": 3, "score": 300},
        {"customer_id": 4, "score": 400},
        {"customer_id": 5, "score": 500},
    ]
    assert w.result.score_total == 1200

    run_frames = [frame for frame in remote.frames if frame.get("type") == "run_task"]
    assert [frame["task_id"] for frame in run_frames] == ["enrichment", "enrichment", "enrichment"]
    assert sorted(frame["args"]["item"] for frame in run_frames) == [3, 4, 5]


@pytest.mark.asyncio
async def test_stdio_remote_environment_reintegrates_into_local_weave(restore_runtime):
    config(
        default_environment="local",
        environments={
            "local": {"executor": "local"},
            "subprocess": {"executor": "stdio"},
        },
    )

    async with weave(seed=8) as w:
        @w.do
        def local_input(seed):
            return seed + 2

        @w.do(environment="subprocess")
        def remote_double(local_input):
            return local_input * 2

        @w.do
        def combined(local_input, remote_double):
            return {"local": local_input, "remote": remote_double}

    assert w.result.combined == {"local": 10, "remote": 20}


@pytest.mark.asyncio
async def test_stdio_remote_imported_functions_reintegrate_into_inline_weave(
    restore_runtime,
    tmp_path,
    monkeypatch,
):
    module_name = "wove_remote_fixture_tasks"
    support_name = "wove_remote_fixture_support"
    (tmp_path / f"{support_name}.py").write_text("SCALE = 11\n", encoding="utf-8")
    (tmp_path / f"{module_name}.py").write_text(
        """
import os

from wove_remote_fixture_support import SCALE


def remote_profile(local_payload):
    value = local_payload["value"]
    return {
        "base": value * SCALE,
        "items": [value + 1, value + 2],
        "worker_pid": os.getpid(),
    }


def remote_enrichment(item, remote_profile):
    return {
        "item": item,
        "score": remote_profile["base"] + item,
        "module": __name__,
        "worker_pid": os.getpid(),
    }
""",
        encoding="utf-8",
    )

    project_root = Path(__file__).resolve().parents[1]
    existing_pythonpath = os.environ.get("PYTHONPATH")
    pythonpath_parts = [str(tmp_path), str(project_root)]
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(pythonpath_parts))
    monkeypatch.syspath_prepend(str(tmp_path))
    for name in (module_name, support_name):
        sys.modules.pop(name, None)
    remote_tasks = importlib.import_module(module_name)

    config(
        default_environment="local",
        environments={
            "local": {"executor": "local"},
            "subprocess": {"executor": "stdio"},
        },
    )

    async with weave(seed=5) as w:
        @w.do
        def local_payload(seed):
            return {"value": seed + 1}

        w.do(environment="subprocess")(remote_tasks.remote_profile)

        @w.do
        def remote_items(remote_profile):
            return remote_profile["items"]

        w.do("remote_items", workers=2, environment="subprocess")(
            remote_tasks.remote_enrichment
        )

        @w.do
        def combined(local_payload, remote_profile, remote_enrichment):
            return {
                "local": local_payload["value"],
                "remote_base": remote_profile["base"],
                "scores": [row["score"] for row in remote_enrichment],
                "modules": [row["module"] for row in remote_enrichment],
                "remote_pids": [
                    remote_profile["worker_pid"],
                    *[row["worker_pid"] for row in remote_enrichment],
                ],
            }

    remote_enrichment = w.result.remote_enrichment
    assert w.result.remote_profile["base"] == 66
    assert [row["item"] for row in remote_enrichment] == [7, 8]
    assert [row["score"] for row in remote_enrichment] == [73, 74]
    assert [row["module"] for row in remote_enrichment] == [module_name, module_name]
    assert w.result.combined["local"] == 6
    assert w.result.combined["remote_base"] == 66
    assert w.result.combined["scores"] == [73, 74]
    assert w.result.combined["modules"] == [module_name, module_name]
    assert all(pid != os.getpid() for pid in w.result.combined["remote_pids"])

    tier_for = {
        task_name: index
        for index, tier in enumerate(w.execution_plan["tiers"])
        for task_name in tier
    }
    assert tier_for["local_payload"] < tier_for["remote_profile"]
    assert tier_for["remote_profile"] < tier_for["remote_items"]
    assert tier_for["remote_items"] < tier_for["remote_enrichment"]
    assert tier_for["remote_enrichment"] < tier_for["combined"]


@pytest.mark.asyncio
async def test_backend_adapter_remote_task_reintegrates_into_local_weave(restore_runtime):
    executor = BackendAdapterEnvironmentExecutor(
        "inline",
        adapter_class=InlineBackendAdapter,
        required_modules=(),
    )
    config(
        default_environment="local",
        environments={
            "local": {"executor": "local"},
            "backend": {"executor": executor},
        },
    )

    async with weave(seed=6) as w:
        @w.do
        def local_payload(seed):
            return {"value": seed}

        @w.do(environment="backend")
        def remote_square(local_payload):
            return local_payload["value"] ** 2

        @w.do
        def combined(local_payload, remote_square):
            return local_payload["value"] + remote_square

    assert w.result.remote_square == 36
    assert w.result.combined == 42


@pytest.mark.asyncio
async def test_mapped_backend_adapter_task_reintegrates_list_result(restore_runtime):
    executor = BackendAdapterEnvironmentExecutor(
        "inline",
        adapter_class=InlineBackendAdapter,
        required_modules=(),
    )
    config(
        default_environment="local",
        environments={
            "local": {"executor": "local"},
            "backend": {"executor": executor},
        },
    )

    async with weave(environment="local") as w:
        @w.do
        def customer_ids():
            return [2, 3, 4]

        @w.do("customer_ids", workers=2, environment="backend")
        def enrichment(item):
            return {"customer_id": item, "score": item * 100}

        @w.do
        def score_total(enrichment):
            return sum(row["score"] for row in enrichment)

        @w.do("enrichment")
        def score_labels(item):
            return f"{item['customer_id']}:{item['score']}"

    assert w.result.enrichment == [
        {"customer_id": 2, "score": 200},
        {"customer_id": 3, "score": 300},
        {"customer_id": 4, "score": 400},
    ]
    assert w.result.score_total == 900
    assert w.result.score_labels == ["2:200", "3:300", "4:400"]


@pytest.mark.asyncio
async def test_optional_adapter_missing_dependency_fails_fast(restore_runtime, monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    config(
        default_environment="celery_env",
        environments={
            "celery_env": {
                "executor": "celery",
                "executor_config": {"command": ["python", "-m", "fake_stdio_worker"]},
            }
        },
    )

    with pytest.raises(RuntimeError, match="celery executor requested"):
        async with weave() as w:
            @w.do
            async def task():
                return 1


@pytest.mark.asyncio
async def test_backend_adapter_uses_callback_delivery(restore_runtime):
    class InlineBackendAdapter(BackendAdapter):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.tasks = []

        async def submit(self, payload, frame):
            del frame
            task = asyncio.create_task(run_backend_payload_async(payload))
            self.tasks.append(task)
            return task

        async def close(self):
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)

    executor = BackendAdapterEnvironmentExecutor(
        "inline",
        adapter_class=InlineBackendAdapter,
        required_modules=(),
    )
    config(
        default_environment="backend",
        environments={
            "backend": {
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
            raise RuntimeError("stdio worker crashed")

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
    assert "stdio worker crashed" in str(w.result.exception)
    assert any("stdio worker crashed" in str(err) for err in w.result._errors.values())


@pytest.mark.asyncio
async def test_backend_environment_receives_raw_sync_callable(restore_runtime):
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
        default_environment="backend",
        environments={"backend": {"executor": capture}},
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
        default_environment="backend",
        environments={
            "backend": {
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
async def test_delivery_timeout_cancels_backend_attempt(restore_runtime):
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
        default_environment="backend",
        environments={
            "backend": {
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
async def test_stdio_executor_uses_default_worker_command(restore_runtime):
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
async def test_delivery_heartbeat_timeout_cancels_backend_attempt(restore_runtime):
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
        default_environment="backend",
        environments={
            "backend": {
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
            "backend": {
                "executor": idle,
                "delivery_orphan_policy": "requeue",
            }
        },
        run_config={},
    )
    await runtime_exec.start()

    loop = asyncio.get_running_loop()
    pending = loop.create_future()
    runtime_exec._pending["backend"]["run-1"] = pending
    runtime_exec._run_metadata["backend"]["run-1"] = {
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

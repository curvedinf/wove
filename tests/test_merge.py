import pytest
import asyncio
import copy
import time
from functools import partial

from wove import config, weave, merge
from wove.environment import EnvironmentExecutor
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


class CaptureExecutor(EnvironmentExecutor):
    def __init__(self):
        self.events = asyncio.Queue()
        self.frames = []
        self.environment_name = None
        self.environment_config = None
        self.run_config = None
        self.tasks = []

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


# --- Functions to be merged ---
async def simple_async_func():
    """A simple async function to be called by merge."""
    await asyncio.sleep(0.01)
    return "async_result"


def simple_sync_func():
    """A simple sync function to be called by merge."""
    return "sync_result"


async def mapped_async_func(item):
    """Async function for mapping test."""
    await asyncio.sleep(0.02)
    return item * 2


def mapped_sync_func(item):
    """Sync function for mapping test."""
    time.sleep(0.02)
    return item * 2


async def async_func_with_args(a, b):
    """Async function with arguments for testing."""
    await asyncio.sleep(0.01)
    return a + b


def sync_func_with_args(a, b=0):
    """Sync function with arguments for testing."""
    return a + b


# --- Test Cases ---
@pytest.mark.asyncio
async def test_merge_async_function():
    """
    Tests that a simple async function can be merged from within an async @w.do task.
    """
    async with weave() as w:

        @w.do
        async def main_task():
            # `merge` returns an awaitable, so it must be awaited.
            result = await merge(simple_async_func)
            return result

    assert w.result.main_task == "async_result"


@pytest.mark.asyncio
async def test_merge_sync_function():
    """
    Tests that a simple sync function can be merged from within an async @w.do task.
    """
    async with weave() as w:

        @w.do
        async def main_task():
            # Wove's merge should handle running the sync function in a thread pool.
            result = await merge(simple_sync_func)
            return result

    assert w.result.main_task == "sync_result"


@pytest.mark.asyncio
async def test_merge_outside_weave_context_raises_runtime_error():
    """
    Tests that calling `merge` outside of an active `weave` context
    raises a RuntimeError.
    """
    with pytest.raises(RuntimeError):
        merge(simple_sync_func)


@pytest.mark.asyncio
async def test_merge_async_mapping():
    """
    Tests that `merge` can map an async function over an iterable concurrently.
    """
    items = [1, 2, 3]
    start_time = time.time()
    async with weave() as w:

        @w.do
        async def main_task():
            return await merge(mapped_async_func, items)

    duration = time.time() - start_time
    # If run serially, would be > 0.06s. Concurrently, should be just over 0.02s.
    assert duration < 0.05
    assert w.result.main_task == [2, 4, 6]


@pytest.mark.asyncio
async def test_merge_sync_mapping():
    """
    Tests that `merge` can map a sync function over an iterable concurrently.
    """
    items = [1, 2, 3]
    start_time = time.time()
    async with weave() as w:

        @w.do
        async def main_task():
            return await merge(mapped_sync_func, items)

    duration = time.time() - start_time
    # If run serially, would be > 0.06s. Concurrently in threads, should be just over 0.02s.
    assert duration < 0.05
    assert w.result.main_task == [2, 4, 6]


@pytest.mark.asyncio
async def test_merge_sync_task_can_call_sync_callable_without_await():
    items = [1, 2, 3]
    async with weave() as w:

        @w.do
        def main_task():
            return merge(mapped_sync_func, items)

    assert w.result.main_task == [2, 4, 6]


@pytest.mark.asyncio
async def test_merge_sync_task_with_one_worker_does_not_deadlock():
    async def run_weave():
        async with weave(max_workers=1) as w:

            @w.do
            def main_task():
                return merge(mapped_sync_func, [1, 2, 3])

        return w.result.main_task

    assert await asyncio.wait_for(run_weave(), timeout=1.0) == [2, 4, 6]


@pytest.mark.asyncio
async def test_merge_sync_task_can_call_async_callable_without_await():
    items = [1, 2, 3]
    async with weave() as w:

        @w.do
        def main_task():
            return merge(mapped_async_func, items)

    assert w.result.main_task == [2, 4, 6]


@pytest.mark.asyncio
async def test_merge_with_arguments_via_partial():
    """
    Tests that arguments can be passed to merged functions using partials.
    """
    async with weave() as w:

        @w.do
        async def main_task():
            # Using partial to pass arguments to an async function
            async_result = await merge(partial(async_func_with_args, 5, 10))
            # Using a lambda to pass arguments to a sync function
            sync_result = await merge(lambda: sync_func_with_args(3, 4))
            return async_result, sync_result

    assert w.result.main_task == (15, 7)


@pytest.mark.asyncio
async def test_merge_retries_sync_callable():
    attempts = 0

    def flaky():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("try again")
        return "ok"

    async with weave() as w:

        @w.do
        async def main_task():
            return await merge(flaky, retries=1)

    assert w.result.main_task == "ok"
    assert attempts == 2


@pytest.mark.asyncio
async def test_merge_forwards_remote_environment_options(restore_runtime):
    remote = CaptureExecutor()
    config(
        default_environment="local",
        environments={
            "local": {"executor": "local"},
            "remote": {"executor": remote, "executor_config": {"region": "test"}},
        },
    )

    async with weave(environment="local", multiplier=3) as w:

        @w.do
        async def main_task(multiplier):
            return await merge(
                lambda item: item * multiplier,
                [1, 2],
                workers=1,
                environment="remote",
                delivery_timeout=7.5,
                delivery_idempotency_key="merge:{item}",
                delivery_cancel_mode="require_ack",
                delivery_orphan_policy="requeue",
            )

    assert w.result.main_task == [3, 6]
    assert remote.environment_name == "remote"
    assert remote.environment_config == {"region": "test"}

    run_frames = [frame for frame in remote.frames if frame.get("type") == "run_task"]
    assert len(run_frames) == 2
    assert [frame["args"]["item"] for frame in run_frames] == [1, 2]
    assert all(frame["task_id"] == "merge:<lambda>" for frame in run_frames)
    assert [frame["delivery"]["delivery_idempotency_key"] for frame in run_frames] == [
        "merge:1",
        "merge:2",
    ]
    assert all(frame["delivery"]["delivery_timeout"] == 7.5 for frame in run_frames)
    assert all(
        frame["delivery"]["delivery_cancel_mode"] == "require_ack"
        for frame in run_frames
    )
    assert all(
        frame["delivery"]["delivery_orphan_policy"] == "requeue"
        for frame in run_frames
    )


@pytest.mark.asyncio
async def test_merge_sync_task_can_dispatch_to_remote_environment(restore_runtime):
    remote = CaptureExecutor()
    config(
        default_environment="local",
        environments={
            "local": {"executor": "local"},
            "remote": {"executor": remote},
        },
    )

    async with weave(environment="local") as w:

        @w.do
        def main_task():
            return merge(lambda item: item + 10, [1, 2], environment="remote")

    assert w.result.main_task == [11, 12]
    run_frames = [frame for frame in remote.frames if frame.get("type") == "run_task"]
    assert len(run_frames) == 2


@pytest.mark.asyncio
async def test_merge_workers_require_iterable():
    async with weave() as w:

        @w.do
        async def main_task():
            return await merge(simple_sync_func, workers=2)

    with pytest.raises(ValueError, match="workers"):
        _ = w.result.main_task


@pytest.mark.asyncio
async def test_merge_recursive_call_raises_error():
    """
    Tests that `merge` detects and prevents deep recursion.
    """

    async def recursive_func(count=0):
        # The implementation stops at > 100, so we recurse past that.
        await merge(lambda: recursive_func(count + 1))

    async with weave() as w:

        @w.do
        async def main_task():
            await merge(recursive_func)

    with pytest.raises(RecursionError, match="Merge call depth exceeded 100"):
        _ = w.result.main_task

import pytest
import time
from wove import weave

@pytest.mark.asyncio
async def test_serial_execution_with_max_workers_1():
    """
    Tests that sync tasks run serially when max_workers=1.
    """
    start_time = time.monotonic()
    async with weave(max_workers=1) as w:
        @w.do
        def task_1():
            time.sleep(0.1)
            return 1
        @w.do
        def task_2():
            time.sleep(0.1)
            return 2
    duration = time.monotonic() - start_time
    # With max_workers=1, tasks should run one after the other.
    # Total time should be at least 0.1 + 0.1 = 0.2 seconds.
    assert duration >= 0.2
    assert w.result['task_1'] == 1
    assert w.result['task_2'] == 2

@pytest.mark.asyncio
async def test_parallel_execution_with_more_workers():
    """
    Tests that sync tasks run in parallel when max_workers > 1.
    """
    start_time = time.monotonic()
    # Using max_workers=2 to allow parallel execution.
    async with weave(max_workers=2) as w:
        @w.do
        def task_1():
            time.sleep(0.1)
            return 1
        @w.do
        def task_2():
            time.sleep(0.1)
            return 2
    duration = time.monotonic() - start_time
    # With parallel execution, total time should be slightly more than 0.1s,
    # but significantly less than 0.2s.
    assert duration < 0.15
    assert w.result['task_1'] == 1
    assert w.result['task_2'] == 2

@pytest.mark.asyncio
async def test_default_executor_is_parallel():
    """
    Tests that the default executor (max_workers=None) runs sync tasks in parallel.
    """
    start_time = time.monotonic()
    async with weave() as w: # max_workers is None by default
        @w.do
        def task_1():
            time.sleep(0.1)
            return 1
        @w.do
        def task_2():
            time.sleep(0.1)
            return 2
    duration = time.monotonic() - start_time
    # Default behavior of ThreadPoolExecutor should be parallel.
    assert duration < 0.15
    assert w.result['task_1'] == 1
    assert w.result['task_2'] == 2

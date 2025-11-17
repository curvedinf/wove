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

@pytest.mark.asyncio
async def test_closure_bug_map_and_regular_tasks_in_same_tier():
    """
    Regression test for issue #15: Closure bug in tier execution.

    Tests that when a tier contains both map tasks and regular tasks,
    the closure variables are captured correctly (by value, not reference).

    Bug symptoms without the fix:
    - Regular tasks fail to save results
    - Map tasks execute with wrong function references
    - TypeError: unexpected keyword argument 'item'
    """
    async with weave() as w:
        # Regular task 1 (no dependencies)
        @w.do
        def regular_task_1():
            return "regular_1"

        # Map task (no dependencies, same tier as regular_task_1)
        @w.do([10, 20, 30])
        def map_task(item):
            return item * 2

        # Regular task 2 (no dependencies, same tier)
        @w.do
        def regular_task_2():
            return "regular_2"

    # All tasks should complete successfully with correct results
    assert w.result.regular_task_1 == "regular_1"
    assert w.result.map_task == [20, 40, 60]
    assert w.result.regular_task_2 == "regular_2"

@pytest.mark.asyncio
async def test_closure_bug_multiple_map_tasks_in_same_tier():
    """
    Regression test for issue #15: Closure bug with multiple map tasks.

    Tests that when a tier contains multiple map tasks with different
    item parameter names, each task correctly uses its own parameters.

    Bug symptoms without the fix:
    - Second map task tries to use first map task's item_param
    - TypeError: unexpected keyword argument
    """
    async with weave() as w:
        # First map task
        @w.do([1, 2, 3])
        def map_task_1(item):
            return item + 100

        # Second map task with same tier (no dependencies)
        @w.do([4, 5, 6])
        def map_task_2(item):
            return item + 200

        # Third map task
        @w.do([7, 8, 9])
        def map_task_3(item):
            return item + 300

    # All map tasks should complete with correct results
    assert w.result.map_task_1 == [101, 102, 103]
    assert w.result.map_task_2 == [204, 205, 206]
    assert w.result.map_task_3 == [307, 308, 309]

import pytest
import asyncio
import time
from wove import weave


@pytest.mark.asyncio
async def test_dependency_execution_order():
    """Tests that tasks execute in the correct dependency order."""
    execution_order = []
    async with weave() as w:

        @w.do
        async def task_a():
            await asyncio.sleep(0.02)
            execution_order.append("a")
            return "A"

        @w.do
        def task_b(task_a):
            execution_order.append("b")
            return f"B after {task_a}"

        @w.do
        async def task_c(task_b):
            await asyncio.sleep(0.01)
            execution_order.append("c")
            return f"C after {task_b}"

    assert execution_order == ["a", "b", "c"]
    assert w.result.task_c == "C after B after A"


@pytest.mark.asyncio
async def test_sync_and_async_tasks():
    """Tests that a mix of sync and async tasks run correctly."""
    async with weave() as w:

        @w.do
        async def async_task():
            await asyncio.sleep(0.01)
            return "async_done"

        @w.do
        def sync_task():
            time.sleep(0.02)  # blocking sleep
            return "sync_done"

        @w.do
        def final_task(async_task, sync_task):
            return f"{async_task} and {sync_task}"

    assert w.result.async_task == "async_done"
    assert w.result.sync_task == "sync_done"
    assert w.result.final == "async_done and sync_done"


@pytest.mark.asyncio
async def test_concurrent_execution():
    """Tests that independent tasks run concurrently."""
    start_time = time.time()
    async with weave() as w:

        @w.do
        async def task_1():
            await asyncio.sleep(0.1)
            return 1

        @w.do
        async def task_2():
            await asyncio.sleep(0.1)
            return 2

    end_time = time.time()
    # If run sequentially, it would take > 0.2s. Concurrently, < 0.2s (but not too much less)
    assert (end_time - start_time) < 0.15
    assert w.result.task_1 == 1
    assert w.result.task_2 == 2


@pytest.mark.asyncio
async def test_result_access_methods():
    """Tests accessing results via dict, unpacking, and .final property."""
    async with weave() as w:

        @w.do
        def first():
            return "one"

        @w.do
        def second(first):
            return "two"

        @w.do
        def third(second):
            return "three"

    # 1. Dictionary-style access
    assert w.result["first"] == "one"
    assert w.result["second"] == "two"
    assert w.result["third"] == "three"

    # Test attribute-style access
    assert w.result.first == "one"

    # 2. Unpacking
    res1, res2, res3 = w.result
    assert res1 == "one"
    assert res2 == "two"
    assert res3 == "three"

    # 3. .final property
    assert w.result.final == "three"


@pytest.mark.asyncio
async def test_error_handling_and_propagation():
    """
    Tests that an exception in one task stops execution, propagates,
    and prevents dependent tasks from running.
    """
    execution_log = []
    async with weave() as w:

        @w.do
        async def successful_task():
            execution_log.append("successful_task")
            await asyncio.sleep(0.01)
            return "success"

        @w.do
        def failing_task(successful_task):
            execution_log.append("failing_task")
            raise ValueError("Task failed")

        @w.do
        def another_task(failing_task):
            # This should not run because its dependency fails
            execution_log.append("another_task")
            return "never runs"

    assert "failing_task" in execution_log
    assert "another_task" not in execution_log, "Dependent task should not have run"
    with pytest.raises(ValueError, match="Task failed"):
        _ = w.result.failing_task
    with pytest.raises(ValueError, match="Task failed"):
        _ = w.result.another_task


@pytest.mark.asyncio
async def test_error_cancels_running_tasks():
    """
    Tests that an exception in one task cancels other concurrently running tasks.
    """
    long_task_started = asyncio.Event()
    long_task_was_cancelled = False
    async with weave() as w:

        @w.do
        async def long_running_task():
            nonlocal long_task_was_cancelled
            long_task_started.set()
            try:
                await asyncio.sleep(0.2)  # Long enough to get cancelled
            except asyncio.CancelledError:
                long_task_was_cancelled = True
                raise
            return "should not finish"

        @w.do
        async def failing_task():
            await long_task_started.wait()
            raise ValueError("Failing task")

    assert long_task_was_cancelled, "The long-running task should have been cancelled"
    with pytest.raises(ValueError, match="Failing task"):
        _ = w.result.failing_task


@pytest.mark.asyncio
async def test_circular_dependency_detection():
    """Tests that a circular dependency raises a RuntimeError."""
    async with weave() as w:

        @w.do
        def task_a(task_c):
            return "a"

        @w.do
        def task_b(task_a):
            return "b"

        @w.do
        def task_c(task_b):
            return "c"

    with pytest.raises(RuntimeError, match="Circular dependency detected"):
        _ = w.result.final


@pytest.mark.asyncio
async def test_task_name_collision_with_result_attributes():
    """
    Tests that defining a task with a name that conflicts with a built-in
    WoveResult attribute raises a NameError.
    """
    with pytest.raises(NameError, match="conflicts with a built-in attribute"):
        async with weave() as w:
            @w.do
            def final():  # "final" is a reserved property on WoveResult
                return "this should not work"

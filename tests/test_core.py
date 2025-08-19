import pytest
import asyncio
import time

from wove import weave, do

@pytest.mark.asyncio
async def test_dependency_execution_order():
    """Tests that tasks execute in the correct dependency order."""
    execution_order = []

    async with weave() as result:
        @do
        async def task_a():
            await asyncio.sleep(0.02)
            execution_order.append("a")
            return "A"

        @do
        def task_b(task_a):
            execution_order.append("b")
            return f"B after {task_a}"

        @do
        async def task_c(task_b):
            await asyncio.sleep(0.01)
            execution_order.append("c")
            return f"C after {task_b}"

    assert execution_order == ["a", "b", "c"]
    assert result['task_c'] == "C after B after A"

@pytest.mark.asyncio
async def test_sync_and_async_tasks():
    """Tests that a mix of sync and async tasks run correctly."""
    async with weave() as result:
        @do
        async def async_task():
            await asyncio.sleep(0.01)
            return "async_done"

        @do
        def sync_task():
            time.sleep(0.02) # blocking sleep
            return "sync_done"
        
        @do
        def final_task(async_task, sync_task):
            return f"{async_task} and {sync_task}"

    assert result['async_task'] == "async_done"
    assert result['sync_task'] == "sync_done"
    assert result.final == "async_done and sync_done"

@pytest.mark.asyncio
async def test_concurrent_execution():
    """Tests that independent tasks run concurrently."""
    start_time = time.time()
    async with weave() as result:
        @do
        async def task_1():
            await asyncio.sleep(0.1)
            return 1
        
        @do
        async def task_2():
            await asyncio.sleep(0.1)
            return 2

    end_time = time.time()
    # If run sequentially, it would take > 0.2s. Concurrently, < 0.2s (but not too much less)
    assert (end_time - start_time) < 0.15
    assert result['task_1'] == 1
    assert result['task_2'] == 2


@pytest.mark.asyncio
async def test_result_access_methods():
    """Tests accessing results via dict, unpacking, and .final property."""
    async with weave() as result:
        @do
        def first():
            return "one"
        
        @do
        def second(first):
            return "two"
            
        @do
        def third(second):
            return "three"

    # 1. Dictionary-style access
    assert result['first'] == "one"
    assert result['second'] == "two"
    assert result['third'] == "three"
    
    # 2. Unpacking
    res1, res2, res3 = result
    assert res1 == "one"
    assert res2 == "two"
    assert res3 == "three"

    # 3. .final property
    assert result.final == "three"


@pytest.mark.asyncio
async def test_error_handling():
    """Tests that an exception in one task stops execution and propagates."""
    with pytest.raises(ValueError, match="Task failed"):
        async with weave() as result:
            @do
            async def successful_task():
                await asyncio.sleep(0.01)
                return "success"
            
            @do
            def failing_task():
                raise ValueError("Task failed")

            @do
            def another_task(failing_task):
                # This should not run
                return "never runs"

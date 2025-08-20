import pytest
import asyncio
import time
from wove import weave, merge

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
    assert w.result.final == "async_result"

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
    assert w.result.final == "sync_result"

@pytest.mark.asyncio
async def test_merge_outside_weave_context_raises_error():
    """
    Tests that calling `merge` outside of an active `weave` context
    raises a RuntimeError.
    """
    with pytest.raises(RuntimeError, match="The `merge` function can only be used inside a task"):
        # The check is synchronous, so the error is raised on call, not on await.
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
    assert w.result.final == [2, 4, 6]

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
    assert w.result.final == [2, 4, 6]

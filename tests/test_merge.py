import pytest
import asyncio
from wove import weave, merge

# --- Functions to be merged ---

async def simple_async_func():
    """A simple async function to be called by merge."""
    await asyncio.sleep(0.01)
    return "async_result"

def simple_sync_func():
    """A simple sync function to be called by merge."""
    return "sync_result"

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

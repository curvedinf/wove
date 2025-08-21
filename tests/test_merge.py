import pytest
import asyncio
import time
from functools import partial
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

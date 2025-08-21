import pytest
import asyncio
from wove import weave


@pytest.mark.asyncio
async def test_timeout_parameter():
    """Tests that a task is cancelled if it exceeds its timeout."""
    async with weave() as w:

        @w.do(timeout=0.01)
        async def long_running_task():
            await asyncio.sleep(0.1)
            return "should not finish"

    with pytest.raises(asyncio.TimeoutError):
        _ = w.result.long_running_task

    # Test that a task that finishes within the timeout is fine
    async with weave() as w:

        @w.do(timeout=0.1)
        async def short_running_task():
            await asyncio.sleep(0.01)
            return "finished"

    assert w.result.final == "finished"


@pytest.mark.asyncio
async def test_retries_on_failure_success():
    """Tests that a task is retried on failure and can eventually succeed."""
    failures = 0

    async with weave() as w:

        @w.do(retries=2)
        async def transient_failure_task():
            nonlocal failures
            if failures < 2:
                failures += 1
                raise ValueError("Transient error")
            return "success"

    assert failures == 2
    assert w.result.final == "success"


@pytest.mark.asyncio
async def test_retries_persistent_failure():
    """Tests that a task that persistently fails raises the last exception after all retries."""
    failures = 0

    async with weave() as w:

        @w.do(retries=3)
        async def persistent_failure_task():
            nonlocal failures
            failures += 1
            raise ValueError("Persistent error")

    assert failures == 4  # Initial attempt + 3 retries
    with pytest.raises(ValueError, match="Persistent error"):
        _ = w.result.persistent_failure_task


@pytest.mark.asyncio
async def test_retries_and_timeout_combined():
    """
    Tests that timeout is applied to each retry attempt, not the whole set of retries.
    """
    attempts = 0

    async with weave(debug=True) as w:

        @w.do(retries=2, timeout=0.05)
        async def slow_flaky_task():
            nonlocal attempts
            attempts += 1
            # The first attempt will fail fast
            if attempts == 1:
                raise ValueError("Flaky error")
            # The second attempt will be slow and time out
            await asyncio.sleep(0.1)
            return "should not finish"

    # Should fail on the third attempt due to timeout, after the first attempt's flaky error.
    assert attempts == 3
    with pytest.raises(asyncio.TimeoutError):
        _ = w.result.slow_flaky_task


@pytest.mark.asyncio
async def test_workers_limit_concurrency():
    """Tests that the `workers` parameter limits concurrency of mapped tasks."""
    max_concurrent = 0
    currently_running = 0
    lock = asyncio.Lock()
    items = list(range(6))
    task_sleep_time = 0.1
    workers = 2

    async def update_concurrency(change):
        nonlocal max_concurrent, currently_running
        async with lock:
            currently_running += change
            if currently_running > max_concurrent:
                max_concurrent = currently_running

    start_time = asyncio.get_event_loop().time()

    async with weave() as w:

        @w.do(items, workers=workers)
        async def limited_task(item):
            await update_concurrency(1)
            await asyncio.sleep(task_sleep_time)
            await update_concurrency(-1)
            return item * 2

    end_time = asyncio.get_event_loop().time()
    total_time = end_time - start_time

    assert w.result.final == [0, 2, 4, 6, 8, 10]
    assert max_concurrent == workers

    # Expected time is (num_items / workers) * sleep_time
    expected_time = (len(items) / workers) * task_sleep_time
    # Allow for some overhead
    assert total_time < expected_time * 1.5


@pytest.mark.asyncio
async def test_limit_per_minute_throttling():
    """Tests that the `limit_per_minute` parameter throttles task creation."""
    items = list(range(4))
    # Limit to 60 per minute, which is 1 per second.
    limit_per_minute = 60
    delay = 60 / limit_per_minute

    start_time = asyncio.get_event_loop().time()

    async with weave() as w:

        @w.do(items, limit_per_minute=limit_per_minute)
        async def throttled_task(item):
            # The task itself is very fast.
            return item

    end_time = asyncio.get_event_loop().time()
    total_time = end_time - start_time

    assert w.result.final == [0, 1, 2, 3]

    # Expected time is (num_items - 1) * delay between tasks.
    expected_time = (len(items) - 1) * delay
    # Allow for some overhead, but it should not be much faster than expected.
    assert total_time > expected_time * 0.9
    assert total_time < expected_time * 1.5

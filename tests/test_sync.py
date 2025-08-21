import pytest
import time
import asyncio
from wove import weave


def test_synchronous_weave_block():
    """
    Tests that the `weave` context manager can be used from a standard
    synchronous function.
    """
    execution_order = []

    # This is a standard `with` block, not `async with`.
    with weave() as w:

        @w.do
        async def async_task_a():
            await asyncio.sleep(0.02)
            execution_order.append("a")
            return "A"

        @w.do
        def sync_task_b(async_task_a):
            # This is a blocking sleep, but it runs in a thread.
            time.sleep(0.01)
            execution_order.append("b")
            return f"B after {async_task_a}"

        @w.do
        def final_task_c(sync_task_b):
            execution_order.append("c")
            return f"C after {sync_task_b}"

    assert execution_order == ["a", "b", "c"]
    assert w.result.final == "C after B after A"


def test_sync_error_propagation():
    """
    Tests that an exception raised inside a synchronous `weave` block
    is correctly propagated.
    """
    with weave() as w:

        @w.do
        def failing_task():
            raise ValueError("Sync failure")

    with pytest.raises(ValueError, match="Sync failure"):
        _ = w.result.failing_task

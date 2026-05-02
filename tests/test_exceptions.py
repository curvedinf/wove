import asyncio
import pytest
import wove.executor as executor_module
from wove import weave
from wove.errors import UnresolvedSignatureError


def test_unresolved_signature_error():
    """
    Tests that a detailed UnresolvedSignatureError is raised for a task
    with dependencies that are not available in the weave.
    """
    with pytest.raises(UnresolvedSignatureError) as exc_info:
        with weave() as w:
            w.do(lambda unavailable_dependency: "will not run")

    error_str = str(exc_info.value)
    assert error_str.startswith("Task '<lambda>' has unresolved dependencies: unavailable_dependency")
    assert "data" in error_str


@pytest.mark.asyncio
async def test_first_exception_is_captured():
    """
    Tests that if multiple tasks fail, the `result.exception` attribute
    is the exception from the first task that failed.
    """
    w = None
    first_exception = ValueError("This should be the captured exception")
    second_exception = TypeError("This should not be captured")

    try:
        async with weave() as w_context:
            w = w_context
            @w.do
            async def fast_fail():
                await asyncio.sleep(0.01)
                raise first_exception

            @w.do
            async def slow_fail():
                await asyncio.sleep(0.02)
                raise second_exception

    except Exception as e:
        # Wove should re-raise the first exception
        assert e is first_exception

    assert w is not None
    assert w.result.exception is first_exception
    assert isinstance(w.result.exception, ValueError)
    assert str(w.result.exception) == "This should be the captured exception"


@pytest.mark.asyncio
async def test_first_exception_uses_completion_order_when_wait_returns_multiple_done(monkeypatch):
    """
    Windows can return multiple failed futures from FIRST_EXCEPTION at once.
    Wove should use the recorded failure time instead of the returned collection order.
    """
    original_wait = executor_module.asyncio.wait

    async def wait_with_reversed_done(futures, *, timeout=None, return_when=asyncio.ALL_COMPLETED):
        futures = list(futures)
        if return_when == asyncio.FIRST_EXCEPTION:
            await original_wait(futures, timeout=timeout, return_when=asyncio.ALL_COMPLETED)
            return list(reversed(futures)), set()
        return await original_wait(futures, timeout=timeout, return_when=return_when)

    monkeypatch.setattr(executor_module.asyncio, "wait", wait_with_reversed_done)

    w = None
    first_exception = ValueError("first")
    second_exception = TypeError("second")

    async with weave() as w_context:
        w = w_context

        @w.do
        async def fast_fail():
            await asyncio.sleep(0.01)
            raise first_exception

        @w.do
        async def slow_fail():
            await asyncio.sleep(0.02)
            raise second_exception

    assert w is not None
    assert w.result.exception is first_exception
    with pytest.raises(ValueError, match="first"):
        _ = w.result.fast_fail

import asyncio
import pytest
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

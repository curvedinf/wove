import pytest
import asyncio
from wove import weave, Weave


class StandardReport(Weave):
    """A reusable Weave template for testing."""

    @Weave.do(retries=2, timeout=5.0)
    async def fetch_data(self, user_id: int):
        return {"id": user_id, "name": "Standard User"}

    @Weave.do
    async def generate_summary(self, fetch_data: dict):
        return f"Report for {fetch_data['name']}"


@pytest.mark.asyncio
async def test_basic_inheritance():
    """Tests that a workflow can be run by passing a Weave class."""
    async with weave(StandardReport, user_id=123) as w:
        # No overrides, just run the parent weave with a seed value.
        pass

    # The tasks from StandardReport should have been executed.
    assert w.result.generate_summary == "Report for Standard User"
    assert w.result.fetch_data == {"id": 123, "name": "Standard User"}


@pytest.mark.asyncio
async def test_task_override():
    """Tests that a task from the parent Weave can be overridden inline."""
    async with weave(StandardReport, user_id=456) as w:

        # This will override the parent's fetch_data
        @w.do
        async def fetch_data(user_id: int):
            return {"id": user_id, "name": "Overridden User"}

    assert w.result.generate_summary == "Report for Overridden User"
    assert w.result.fetch_data == {"id": 456, "name": "Overridden User"}


@pytest.mark.asyncio
async def test_parameter_inheritance_and_override():
    """
    Tests that overridden tasks inherit parameters from the parent,
    and can also override them.
    """
    failure_attempts = 0

    class ReportWithFailingTask(StandardReport):
        @Weave.do(retries=1)
        async def always_fail(self):
            raise ValueError("This should fail")

    async with weave(ReportWithFailingTask, user_id=0) as w:
        # This override inherits `retries=2` from the parent,
        # but overrides `timeout` from 5.0 to 0.01.
        @w.do(timeout=0.01)
        async def fetch_data(user_id: int):
            # This should time out because of the new timeout.
            await asyncio.sleep(0.1)
            return "should not complete"

        # This override inherits `retries=1` and should fail once, then succeed.
        # Note: no `self` parameter, as this is not a method of the class.
        @w.do
        async def always_fail():
            nonlocal failure_attempts
            failure_attempts += 1
            if failure_attempts <= 1:
                raise ValueError("First failure")
            return "success"

    # Check that fetch_data timed out by accessing its result.
    # Wove stores the exception and re-raises it on access.
    with pytest.raises(asyncio.TimeoutError):
        _ = w.result.fetch_data

    # Check that always_fail was retried and succeeded
    assert failure_attempts == 2
    assert w.result.always_fail == "success"


@pytest.mark.asyncio
async def test_adding_new_task_to_inherited_weave():
    """Tests that new tasks can be added to an inherited workflow."""
    async with weave(StandardReport, user_id=789) as w:

        @w.do
        def extra_analysis(generate_summary: str):
            return f"Extra analysis on: '{generate_summary}'"

    assert w.result.generate_summary == "Report for Standard User"
    assert w.result.extra_analysis == "Extra analysis on: 'Report for Standard User'"

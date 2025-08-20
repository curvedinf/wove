import pytest
import asyncio
import re
import time
from wove import weave

def strip_ansi(text):
    """Helper to clean ANSI color codes from output for easier comparison."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


@pytest.mark.asyncio
async def test_debug_output_capturing(capsys):
    """Tests that debug=True prints a report to stdout."""
    async with weave(debug=True) as w:
        @w.do
        def task_a():
            return 1

        @w.do
        def task_b(task_a):
            return task_a + 1

    captured = capsys.readouterr()
    output = strip_ansi(captured.out)
    assert "--- Wove Debug Report ---" in output
    assert "Detected Tasks (2):" in output
    assert "• task_a" in output
    assert "• task_b" in output
    assert "Dependency Graph:" in output
    assert "Execution Plan:" in output
    assert "Tier 1" in output
    assert "- task_a" in output
    assert "Tier 2" in output
    assert "- task_b" in output
    assert "--- Starting Execution ---" in output


@pytest.mark.asyncio
async def test_debug_output_content_and_tags(capsys):
    """
    Tests that the debug output correctly identifies sync/async tasks
    and mapping information.
    """
    items = list(range(3))
    async with weave(debug=True) as w:
        @w.do
        async def async_task():
            await asyncio.sleep(0.01)
            return "async"

        @w.do(items)
        def mapped_sync_task(item, async_task):
            return f"{async_task}-{item}"

    captured = capsys.readouterr()
    output = strip_ansi(captured.out)
    # Check for async tag
    assert "- async_task (async)" in output
    # Check for sync and mapping tags
    assert "- mapped_sync_task (sync) [mapped over 3 items]" in output
    # Check dependencies in graph report
    # This is a bit brittle, but checks for key phrases.
    assert "• async_task" in output
    assert "Dependents:   mapped_sync_task" in output
    assert "• mapped_sync_task" in output
    assert "Dependencies: async_task" in output


@pytest.mark.asyncio
async def test_programmatic_access_to_execution_plan():
    """
    Tests that the execution_plan is available on the context manager
    after the block exits.
    """
    async with weave() as w:
        @w.do
        def task_a():
            pass

        @w.do
        def task_b(task_a):
            pass

    plan = w.execution_plan
    assert plan is not None
    assert "dependencies" in plan
    assert "dependents" in plan
    assert "tiers" in plan
    assert "sorted_tasks" in plan
    assert plan["dependencies"] == {"task_a": set(), "task_b": {"task_a"}}
    assert plan["dependents"] == {"task_a": {"task_b"}, "task_b": set()}
    assert plan["tiers"] == [["task_a"], ["task_b"]]
    assert plan["sorted_tasks"] == ["task_a", "task_b"]


@pytest.mark.asyncio
async def test_task_timings_are_recorded():
    """
    Tests that task execution times are recorded in w.result.timings.
    """
    async with weave() as w:
        @w.do
        async def task_a():
            await asyncio.sleep(0.02)

        @w.do
        def task_b():
            time.sleep(0.03)

    timings = w.result.timings
    assert "task_a" in timings
    assert "task_b" in timings
    assert timings["task_a"] >= 0.02
    assert timings["task_b"] >= 0.03


@pytest.mark.asyncio
async def test_debug_false_produces_no_output(capsys):
    """Tests that debug=False (the default) produces no stdout report."""
    async with weave() as w:
        @w.do
        def task_a():
            return 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.asyncio
async def test_debug_report_essentials(capsys):
    """Checks for the presence of essential sections in the debug report."""
    async with weave(debug=True) as w:
        @w.do
        def task_one():
            pass

        @w.do
        def task_two(task_one):
            pass

    captured = capsys.readouterr()
    output = strip_ansi(captured.out)
    assert "--- Wove Debug Report ---" in output
    assert "Dependency Graph:" in output
    assert "Execution Plan:" in output

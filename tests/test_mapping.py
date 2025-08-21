import pytest
import asyncio
import time
from wove import weave


@pytest.mark.asyncio
async def test_basic_mapping():
    """Tests that a task can be mapped over a simple iterable."""
    items = [1, 2, 3]
    async with weave() as w:

        @w.do(items)
        async def process_item(item):
            await asyncio.sleep(0.01)
            return item * 2

    assert w.result.process_item == [2, 4, 6]


@pytest.mark.asyncio
async def test_mapping_with_dependency():
    """Tests that a mapped task can depend on another task."""
    items = [10, 20]
    async with weave() as w:

        @w.do
        def multiplier():
            return 3

        @w.do(items)
        def process_item_with_dep(item, multiplier):
            return item * multiplier

    assert w.result.process_item_with_dep == [30, 60]


@pytest.mark.asyncio
async def test_mapping_over_empty_list():
    """Tests that mapping over an empty list produces an empty list and does not run the function."""
    was_called = False
    async with weave() as w:

        @w.do([])
        def process_item(item):
            nonlocal was_called
            was_called = True
            # This should never run
            return item * 2

    assert w.result.process_item == []
    assert not was_called, "Mapped function should not be called for an empty iterable."


@pytest.mark.asyncio
async def test_sync_function_mapping():
    """Tests mapping over an iterable with a synchronous function."""
    items = [0.01, 0.01, 0.01]
    start_time = time.time()
    async with weave() as w:

        @w.do(items)
        def sync_process(item):
            time.sleep(item)
            return True

    duration = time.time() - start_time
    # If run in series, would be > 0.03. Concurrently in threads, should be less.
    assert duration < 0.025
    assert w.result.sync_process == [True, True, True]


@pytest.mark.asyncio
async def test_downstream_task_uses_mapped_results():
    """Tests that a subsequent task can use the collected results of a mapped task."""
    items = [1, 2, 3]
    async with weave() as w:

        @w.do(items)
        def square(item):
            return item * item

        @w.do
        def sum_squares(square):
            return sum(square)

    assert w.result.sum_squares == 14  # 1 + 4 + 9
    assert w.result.square == [1, 4, 9]


@pytest.mark.asyncio
async def test_mapped_task_signature_validation():
    """Tests that a mapped task with an incorrect signature raises a TypeError."""
    async with weave() as w:

        @w.do([1, 2, 3])
        def no_item_param():
            return 1

    with pytest.raises(TypeError, match="must have exactly one parameter that is not a dependency"):
        _ = w.result.no_item_param


@pytest.mark.asyncio
async def test_fundamental_mapping():
    """Tests that decorating a function with @w.do([1, 2, 3]) executes it for each item."""
    async with weave() as w:

        @w.do([1, 2, 3])
        def process(item):
            return item * 2

    assert w.result.process == [2, 4, 6]


@pytest.mark.asyncio
async def test_mapping_with_async_dependency():
    """Tests that a mapped task can depend on a preceding, non-mapped, async task."""
    items = [10, 20]
    async with weave() as w:

        @w.do
        async def multiplier():
            await asyncio.sleep(0.01)
            return 3

        @w.do(items)
        def process_item_with_dep(item, multiplier):
            return item * multiplier

    assert w.result.process_item_with_dep == [30, 60]


@pytest.mark.asyncio
async def test_async_downstream_task_uses_mapped_results():
    """Tests an async downstream task using async mapped results."""
    items = [1, 2, 3]
    async with weave() as w:

        @w.do(items)
        async def square_async(item):
            await asyncio.sleep(0.01)
            return item * item

        @w.do
        async def sum_squares_async(square_async):
            await asyncio.sleep(0.01)
            return sum(square_async)

    assert w.result.sum_squares_async == 14
    assert w.result.square_async == [1, 4, 9]


@pytest.mark.asyncio
async def test_error_in_map_cancels_others():
    """Tests that an exception in one mapped sub-task cancels others."""
    items = ["ok_long", "fail", "ok"]

    long_task_started = asyncio.Event()
    long_task_cancelled = False
    async with weave() as w:

        @w.do(items)
        async def process_item_with_failure(item):
            nonlocal long_task_cancelled
            if item == "ok":
                await asyncio.sleep(0.1)  # should get cancelled
                return "ok"
            elif item == "fail":
                await long_task_started.wait()  # Make sure the long one starts
                raise ValueError("Task failed on item: fail")
            elif item == "ok_long":
                long_task_started.set()
                try:
                    await asyncio.sleep(0.2)  # Long enough to be cancelled
                except asyncio.CancelledError:
                    long_task_cancelled = True
                    raise
                return "long_ok"

    assert long_task_cancelled, "The long-running sub-task should have been cancelled."
    with pytest.raises(ValueError, match="Task failed on item: fail"):
        _ = w.result.process_item_with_failure

@pytest.mark.asyncio
async def test_mapping_over_async_task_result():
    """Tests mapping over the result of a preceding async task."""
    async with weave() as w:
        @w.do
        async def source_task():
            await asyncio.sleep(0.01)
            return [1, 2, 3]

        @w.do("source_task")
        def mapped_task(item):
            return item * 2

    assert w.result.mapped_task == [2, 4, 6]
    assert w.result.source_task == [1, 2, 3]


@pytest.mark.asyncio
async def test_mapping_over_sync_task_result():
    """Tests mapping over the result of a preceding sync task."""
    async with weave() as w:
        @w.do
        def source_task():
            return ["a", "b"]

        @w.do("source_task")
        async def mapped_task(item):
            await asyncio.sleep(0.01)
            return item.upper()

    assert w.result.mapped_task == ["A", "B"]
    assert w.result.source_task == ["a", "b"]


@pytest.mark.asyncio
async def test_mapping_over_task_returning_empty_list():
    """Tests mapping over a task that returns an empty list."""
    was_called = False
    async with weave() as w:
        @w.do
        async def source_task():
            return []

        @w.do("source_task")
        def mapped_task(item):
            nonlocal was_called
            was_called = True
            return item * 2

    assert w.result.mapped_task == []
    assert not was_called, "Mapped function should not be called for an empty iterable."


@pytest.mark.asyncio
async def test_mapping_over_nonexistent_task_raises_error():
    """Tests that mapping over a non-existent task name raises a NameError."""
    async with weave() as w:
        @w.do("nonexistent_task")
        def mapped_task(item):
            return item

    with pytest.raises(NameError, match="depends on 'nonexistent_task'"):
        _ = w.result.mapped_task

@pytest.mark.asyncio
async def test_mapping_over_non_iterable_task_result():
    """Tests that mapping over a task that returns a non-iterable raises a TypeError."""
    async with weave() as w:
        @w.do
        def source_task_non_iterable():
            return 123  # Not iterable

        @w.do("source_task_non_iterable")
        def mapped_task_on_non_iterable(item):
            return item * 2

    with pytest.raises(TypeError, match="result of type 'int' is not iterable"):
        _ = w.result.mapped_task_on_non_iterable

@pytest.mark.asyncio
async def test_chained_dynamic_mapping():
    """Tests that a mapped task can be chained over the result of another mapped task."""
    async with weave() as w:
        @w.do
        async def task_a():
            """Generates the initial iterable."""
            return [1, 2]

        @w.do("task_a")
        def task_b(item):
            """First level of mapping."""
            return item * 10

        @w.do("task_b")
        async def task_c(item):
            """Second level of mapping, depends on the result of task_b."""
            await asyncio.sleep(0.01)
            return item + 1

    assert w.result.task_a == [1, 2]
    assert w.result.task_b == [10, 20]
    assert w.result.task_c == [11, 21]

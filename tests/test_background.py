import asyncio
import os
import pytest
from wove import weave
from tests.test_data import MyTestData

@pytest.mark.asyncio
async def test_threaded_background_processing():
    """
    Tests that a weave can be executed in the background using a thread.
    """
    execution_result = None
    event = asyncio.Event()

    def on_done(result):
        nonlocal execution_result
        execution_result = result.a
        event.set()

    async with weave(background=True, on_done=on_done) as w:
        @w.do
        def a():
            return 1

    await asyncio.wait_for(event.wait(), timeout=2)
    assert execution_result == 1

@pytest.mark.asyncio
async def test_forked_background_processing():
    """
    Tests that a weave can be executed in the background using a forked process.
    """
    # We will use a file to signal completion from the forked process
    completion_file = "fork_completion.txt"
    if os.path.exists(completion_file):
        os.remove(completion_file)

    # This on_done function is what will be pickled and run in the new process.
    def on_done(result):
        with open(completion_file, "w") as f:
            f.write(str(result.a))

    async with weave(background=True, fork=True, on_done=on_done) as w:
        @w.do
        def a():
            return 2

    # Wait for the forked process to finish and write the file.
    for _ in range(40): # wait up to 4 seconds
        if os.path.exists(completion_file):
            break
        await asyncio.sleep(0.1)

    with open(completion_file, "r") as f:
        execution_result = int(f.read())

    os.remove(completion_file)

    assert execution_result == 2


@pytest.mark.asyncio
async def test_forked_background_processing_with_complex_data():
    """
    Tests that a forked weave can handle complex data, including class instances
    and closures that reference local variables.
    """
    completion_file = "fork_complex_completion.txt"
    if os.path.exists(completion_file):
        os.remove(completion_file)

    local_variable = 10
    test_instance = MyTestData(20)

    # This on_done function will be pickled and run in the new process.
    # It will verify that the complex data was correctly serialized.
    def on_done(result):
        with open(completion_file, "w") as f:
            f.write(str(result.final_result))

    async with weave(background=True, fork=True, on_done=on_done, initial_data=test_instance) as w:
        @w.do
        def process_data(initial_data):
            # This function uses a local variable from the parent process's scope (a closure)
            # and a class instance passed as initial data.
            return initial_data.value + local_variable

        @w.do
        def final_result(process_data):
            return process_data * 2


    # Wait for the forked process to finish and write the file.
    for _ in range(40): # wait up to 4 seconds
        if os.path.exists(completion_file):
            break
        await asyncio.sleep(0.1)

    with open(completion_file, "r") as f:
        execution_result = int(f.read())

    os.remove(completion_file)

    # Expected result: (test_instance.value + local_variable) * 2 = (20 + 10) * 2 = 60
    assert execution_result == 60

@pytest.mark.asyncio
async def test_background_mode_no_callback():
    """
    Tests that background mode works correctly without an on_done callback.
    """
    async with weave(background=True) as w:
        @w.do
        def a():
            return 1
    # Give the thread a moment to start and run.
    # The main point is that this doesn't raise an error.
    await asyncio.sleep(0.5)

@pytest.mark.asyncio
async def test_threaded_background_task_failure():
    """
    Tests that if a task fails in a background thread, the exception is
    contained within the WoveResult and passed to the on_done callback.
    """
    error_in_result = None
    event = asyncio.Event()

    def on_done(result):
        nonlocal error_in_result
        error_in_result = result._errors.get("a")
        event.set()

    async with weave(background=True, on_done=on_done) as w:
        @w.do
        def a():
            raise ValueError("Task failed")

    await asyncio.wait_for(event.wait(), timeout=2)
    assert isinstance(error_in_result, ValueError)
    assert str(error_in_result) == "Task failed"

def test_sync_exit_with_exception():
    """
    Tests that the synchronous __exit__ method correctly handles an exception
    occurring within the `with` block, ensuring it exits cleanly.
    """
    try:
        with weave() as w:
            @w.do
            def a():
                return 1
            raise ValueError("Something went wrong")
    except ValueError as e:
        assert str(e) == "Something went wrong"
    # If this completes without hanging or raising a different error, it's a success.

@pytest.mark.asyncio
async def test_async_aexit_with_exception():
    """
    Tests that the asynchronous __aexit__ method correctly handles an exception
    and shuts down gracefully.
    """
    try:
        async with weave() as w:
            @w.do
            def a():
                return 1
            # Simulate a failure before the weave block completes
            raise ValueError("Async error")
    except ValueError as e:
        assert str(e) == "Async error"
    # The test passes if it exits cleanly without other errors.


@pytest.mark.asyncio
async def test_threaded_background_exception_attribute():
    """
    Tests that result.exception is set correctly in threaded background mode.
    """
    execution_exception = None
    event = asyncio.Event()

    def on_done(result):
        nonlocal execution_exception
        execution_exception = result.exception
        event.set()

    async with weave(background=True, on_done=on_done) as w:
        @w.do
        def a():
            raise ValueError("Threaded background task failed")

    await asyncio.wait_for(event.wait(), timeout=2)
    assert isinstance(execution_exception, ValueError)
    assert str(execution_exception) == "Threaded background task failed"


@pytest.mark.asyncio
async def test_forked_background_exception_attribute():
    """
    Tests that result.exception is set correctly in forked background mode.
    """
    completion_file = "fork_exception_completion.txt"
    if os.path.exists(completion_file):
        os.remove(completion_file)

    def on_done(result):
        if result.exception:
            with open(completion_file, "w") as f:
                f.write(str(result.exception))

    async with weave(background=True, fork=True, on_done=on_done) as w:
        @w.do
        def a():
            raise ValueError("Forked background task failed")

    for _ in range(40):
        if os.path.exists(completion_file):
            break
        await asyncio.sleep(0.1)

    with open(completion_file, "r") as f:
        execution_result = f.read()

    os.remove(completion_file)

    assert execution_result == "Forked background task failed"

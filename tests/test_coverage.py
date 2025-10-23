import asyncio
import pytest
from wove import weave, WoveResult

@pytest.mark.asyncio
async def test_task_name_conflict():
    with pytest.raises(NameError):
        async with weave() as w:
            @w.do
            def cancelled():
                return 1

@pytest.mark.asyncio
async def test_result_getitem_with_error():
    w = weave()
    async with w:
        @w.do
        def a():
            raise ValueError("Task failed")
    with pytest.raises(ValueError):
        _ = w.result["a"]

@pytest.mark.asyncio
async def test_result_getattr_with_error():
    w = weave()
    async with w:
        @w.do
        def a():
            raise ValueError("Task failed")
    with pytest.raises(ValueError):
        _ = w.result.a

@pytest.mark.asyncio
async def test_result_final_with_error():
    w = weave()
    async with w:
        @w.do
        def a():
            return 1
        @w.do
        def b(a):
            raise ValueError("Task failed")
    with pytest.raises(ValueError):
        _ = w.result.final

@pytest.mark.asyncio
async def test_result_final_no_tasks():
    async with weave() as w:
        pass
    assert w.result.final is None

@pytest.mark.asyncio
async def test_debug_mode(capsys):
    async with weave(debug=True) as w:
        @w.do
        def a():
            return 1
    captured = capsys.readouterr()
    assert "Execution Plan" in captured.out

def test_workers_without_map():
    with pytest.raises(ValueError):
        with weave() as w:
            @w.do(workers=2)
            def a():
                return 1

@pytest.mark.asyncio
async def test_task_timeout():
    w = weave()
    with pytest.raises(asyncio.CancelledError):
        async with w:
            @w.do(timeout=0.1)
            async def a():
                await asyncio.sleep(1)
    assert "a" in w.result.cancelled

@pytest.mark.asyncio
async def test_task_retries():
    attempts = 0
    async with weave() as w:
        @w.do(retries=2)
        def a():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError("Task failed")
            return "Success"
    assert w.result.a == "Success"
    assert attempts == 3

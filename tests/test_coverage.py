import asyncio
import pytest
from wove import weave, WoveResult, Weave

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


def test_wove_result_additional_branches():
    with pytest.raises(ValueError, match="error_mode"):
        WoveResult(error_mode="invalid")

    result = WoveResult(error_mode="return")
    result._add_result("x", 1)
    result._definition_order.append("x")
    result._add_error("y", ValueError("bad"))
    result._definition_order.append("y")

    assert len(result) == 1
    assert result.y.__class__ is ValueError
    assert result.final.__class__ is ValueError

    with pytest.raises(AttributeError):
        _ = result.missing


def test_weave_class_do_validates_delivery_contracts():
    with pytest.raises(ValueError, match="delivery_cancel_mode"):
        @Weave.do(delivery_cancel_mode="invalid")
        def a(self):
            return 1

    with pytest.raises(ValueError, match="delivery_orphan_policy"):
        @Weave.do(delivery_orphan_policy="invalid")
        def b(self):
            return 1


def test_weave_invalid_error_mode_raises():
    with pytest.raises(ValueError, match="error_mode"):
        weave(error_mode="invalid")


def test_weave_initial_value_name_conflicts():
    with pytest.raises(NameError, match="conflicts with a built-in attribute"):
        weave(final=1)

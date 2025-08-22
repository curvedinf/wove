import pytest
from wove import weave, Weave

@pytest.mark.asyncio
async def test_basic_kwarg_injection():
    """Tests that a single keyword argument is injected into a task."""
    async with weave(user_id=123) as w:
        @w.do
        def check_user_id(user_id: int):
            return user_id * 2

    assert w.result.final == 246

@pytest.mark.asyncio
async def test_multiple_kwarg_injection():
    """Tests that multiple keyword arguments are injected correctly."""
    async with weave(a=10, b=20) as w:
        @w.do
        def add_them(a, b):
            return a + b

    assert w.result.final == 30

@pytest.mark.asyncio
async def test_data_object_injection():
    """Tests that the entire 'data' object is injected correctly."""
    async with weave(a=10, b=20, c="hello") as w:
        @w.do
        def get_the_data(data: dict):
            return data

    assert w.result.final == {"a": 10, "b": 20, "c": "hello"}

@pytest.mark.asyncio
async def test_kwarg_and_data_object_injection():
    """Tests that a task can receive both a specific kwarg and the full data object."""
    async with weave(a=10, b=20) as w:
        @w.do
        def check_both(a: int, data: dict):
            return data['b'] + a

    assert w.result.final == 30

@pytest.mark.asyncio
async def test_injection_into_weave_class_method():
    """Tests that kwargs are injected into methods of a Weave class."""
    class MyWorkflow(Weave):
        @Weave.do
        def process(self, user_id: int, factor: int):
            return user_id * factor

    async with weave(MyWorkflow, user_id=10, factor=5) as w:
        pass

    assert w.result.final == 50

@pytest.mark.asyncio
async def test_injection_into_overridden_task():
    """Tests that kwargs are injected into an overridden task."""
    class MyWorkflow(Weave):
        @Weave.do
        def process(self, user_id: int):
            return user_id # This should not run

    async with weave(MyWorkflow, user_id=100, message="hello") as w:
        @w.do
        def process(user_id: int, message: str):
            return f"{message} {user_id}"

    assert w.result.final == "hello 100"

@pytest.mark.asyncio
async def test_late_binding_signature_change():
    """
    Tests that the dependency graph respects the final signature of an
    overridden task, not the original signature from the parent class.
    """
    class MyWorkflow(Weave):
        @Weave.do
        def my_task(self, db_connection): # Original depends on db_connection
            return "original"

    # Pass api_key, which is what the *new* task will need.
    # Do not pass db_connection. If the graph isn't built with the final
    # signature, this will fail.
    async with weave(MyWorkflow, api_key="xyz") as w:
        @w.do
        def my_task(api_key: str): # Override has a different signature
            return f"new-{api_key}"

    assert w.result.final == "new-xyz"

@pytest.mark.asyncio
async def test_missing_dependency_error():
    """Tests that a NameError is raised if a dependency is not provided."""
    with pytest.raises(NameError):
        async with weave() as w:
            @w.do
            def needs_something(unprovided_variable):
                return unprovided_variable

@pytest.mark.asyncio
async def test_reserved_data_keyword_error():
    """Tests that using 'data' as a keyword argument raises a NameError."""
    with pytest.raises(NameError, match="'data' is a reserved name"):
        async with weave(data={"a": 1}) as w:
            pass

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

    assert "Task '<lambda>' has unresolved dependencies: unavailable_dependency" in str(exc_info.value)
    assert "Available dependencies: data" in str(exc_info.value)

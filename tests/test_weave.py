import pytest
from wove import Weave


def test_instantiating_weave_class_outside_context_fails():
    """
    Tests that trying to instantiate a Weave-derived class directly
    raises a TypeError with a helpful message.
    """
    class MyWorkflow(Weave):
        pass

    with pytest.raises(TypeError, match="cannot be instantiated directly"):
        MyWorkflow()

    with pytest.raises(TypeError, match="Instead, pass the class"):
        MyWorkflow()

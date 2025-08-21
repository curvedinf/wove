import pytest
from wove import helpers


def test_flatten():
    """Tests the flatten helper function."""
    assert helpers.flatten([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]
    assert helpers.flatten([[], [1], [], [2, 3]]) == [1, 2, 3]
    assert helpers.flatten([]) == []
    assert helpers.flatten([("a", "b"), ("c",)]) == ["a", "b", "c"]


def test_fold():
    """Tests the fold helper function."""
    assert helpers.fold([1, 2, 3, 4, 5, 6], 2) == [[1, 2], [3, 4], [5, 6]]
    assert helpers.fold([1, 2, 3, 4, 5, 6], 3) == [[1, 2, 3], [4, 5, 6]]
    # Test with an uneven final chunk
    assert helpers.fold([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert helpers.fold([], 2) == []
    with pytest.raises(ValueError):
        # Folding with size 0 should not be allowed.
        helpers.fold([1, 2, 3], 0)


def test_batch():
    """Tests the batch helper function."""
    # Test with a list that can be evenly divided
    assert helpers.batch([1, 2, 3, 4, 5, 6], 2) == [[1, 2, 3], [4, 5, 6]]
    assert helpers.batch([1, 2, 3, 4, 5, 6], 3) == [[1, 2], [3, 4], [5, 6]]

    # Test with an uneven final chunk
    assert helpers.batch([1, 2, 3, 4, 5], 2) == [[1, 2, 3], [4, 5]]
    assert helpers.batch([1, 2, 3, 4, 5], 3) == [[1, 2], [3, 4], [5]]

    # Test with a count larger than the list size
    assert helpers.batch([1, 2, 3], 5) == [[1], [2], [3]]

    # Test with an empty list
    assert helpers.batch([], 3) == []

    # Test with invalid count
    with pytest.raises(ValueError):
        helpers.batch([1, 2, 3], 0)


def test_undict():
    """Tests the undict helper function."""
    assert helpers.undict({"a": 1, "b": 2}) == [("a", 1), ("b", 2)]
    assert helpers.undict({}) == []


def test_redict():
    """Tests the redict helper function."""
    assert helpers.redict([("a", 1), ("b", 2)]) == {"a": 1, "b": 2}
    assert helpers.redict([]) == {}
    # Test that it correctly overwrites earlier keys
    assert helpers.redict([("a", 1), ("b", 2), ("a", 3)]) == {"a": 3, "b": 2}


def test_denone():
    """Tests the denone helper function."""
    assert helpers.denone([1, None, 2, 3, None]) == [1, 2, 3]
    assert helpers.denone([None, None, None]) == []
    assert helpers.denone([1, 2, 3]) == [1, 2, 3]
    assert helpers.denone([]) == []
    # Test with other "falsy" values that should be kept
    assert helpers.denone([1, 0, 2, "", False]) == [1, 0, 2, "", False]

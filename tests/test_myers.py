"""Tests for the Myers core: correctness, minimality, edge cases."""

import random

import pytest

from textdiff.myers import Op, apply_to, diff, edit_distance


def _dp_distance(a, b):
    """Independent edit distance via classic DP (insert/delete only)."""
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(
                prev[j] + 1,  # delete x
                cur[j - 1] + 1,  # insert y
                prev[j - 1] + (0 if x == y else 2),  # substitute = del + ins
            )
        prev = cur
    return prev[-1]


def test_empty_sequences():
    assert diff([], []) == []
    assert diff([], ["a"]) == [Op("insert", None, 0)]
    assert diff(["a"], []) == [Op("delete", 0, None)]


def test_identical_sequences():
    ops = diff(["a", "b", "c"], ["a", "b", "c"])
    assert all(op.kind == "equal" for op in ops)
    assert len(ops) == 3


def test_simple_insertion_and_deletion():
    ops = diff(["a", "b", "c"], ["a", "x", "b", "c"])
    assert apply_to(["a", "b", "c"], ["a", "x", "b", "c"], ops) == ["a", "x", "b", "c"]
    assert edit_distance(["a", "b", "c"], ["a", "x", "b", "c"]) == 1


def test_repeated_elements():
    # Repeated lines are where naive diffs go wrong: the script must still
    # be shortest and must reconstruct b exactly.
    a = ["x", "x", "y", "x"]
    b = ["x", "y", "x", "x"]
    ops = diff(a, b)
    assert apply_to(a, b, ops) == b
    assert edit_distance(a, b) == _dp_distance(a, b)


def test_completely_different():
    a = list("abc")
    b = list("xyz")
    ops = diff(a, b)
    assert apply_to(a, b, ops) == b
    assert edit_distance(a, b) == 6


@pytest.mark.parametrize("seed", range(20))
def test_random_sequences_are_shortest_and_reconstruct(seed):
    rng = random.Random(seed)
    alphabet = ["a", "b", "c"]
    a = [rng.choice(alphabet) for _ in range(rng.randint(0, 12))]
    b = [rng.choice(alphabet) for _ in range(rng.randint(0, 12))]
    ops = diff(a, b)
    assert apply_to(a, b, ops) == b
    assert edit_distance(a, b) == _dp_distance(a, b)


def test_edit_distance_symmetry():
    assert edit_distance("kitten", "sitting") == edit_distance("sitting", "kitten")


def test_ops_indices_are_in_range():
    a = list("abcdef")
    b = list("azcdey")
    for op in diff(a, b):
        if op.kind in ("equal", "delete"):
            assert op.a_index is not None and 0 <= op.a_index < len(a)
        if op.kind in ("equal", "insert"):
            assert op.b_index is not None and 0 <= op.b_index < len(b)

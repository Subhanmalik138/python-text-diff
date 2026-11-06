"""Myers O(ND) diff algorithm.

Computes a *shortest* edit script between two sequences: the minimum number
of insertions and deletions needed to turn ``a`` into ``b``.

The implementation follows Myers (1986), "An O(ND) Algorithm and its
Variations": a greedy forward pass records, for every edit distance ``d``,
the furthest point reachable on each diagonal ``k = x - y``; a backward pass
then walks the recorded trace to recover one shortest script.

The algorithm is generic over the sequence elements — lines, words, tokens,
bytes — so the same core powers the line diff, the word diff and the CLI.

Complexity: O(ND) time where D is the edit distance, O(D**2) space for the
full trace. For the small-to-medium inputs this tool targets (source files,
config files, prose) that is the right trade-off: the code stays short and
obviously correct. For multi-megabyte inputs, a linear-space variant or
``difflib`` would be the better choice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Op:
    """One step of an edit script.

    ``kind`` is one of ``"equal"``, ``"insert"`` or ``"delete"``.
    ``a_index`` is the index into the old sequence (``None`` for inserts)
    and ``b_index`` the index into the new sequence (``None`` for deletes).
    """

    kind: str
    a_index: int | None
    b_index: int | None


def diff(a: Sequence[T], b: Sequence[T]) -> list[Op]:
    """Return a shortest edit script turning ``a`` into ``b``.

    Applying the returned ops to ``a`` (keep ``"equal"`` elements, drop
    ``"delete"`` elements, insert ``"insert"`` elements in order) yields
    exactly ``b``.
    """
    trace = _forward(a, b)
    return _backtrack(trace, a, b)


def edit_distance(a: Sequence[T], b: Sequence[T]) -> int:
    """Minimum number of insertions + deletions needed to turn ``a`` into ``b``."""
    return sum(1 for op in diff(a, b) if op.kind != "equal")


def apply_to(a: Sequence[T], b: Sequence[T], ops: list[Op]) -> list[T]:
    """Apply an edit script to ``a`` using ``b`` as the source of insertions."""
    out: list[T] = []
    for op in ops:
        if op.kind == "equal":
            assert op.a_index is not None
            out.append(a[op.a_index])
        elif op.kind == "insert":
            assert op.b_index is not None
            out.append(b[op.b_index])
        elif op.kind == "delete":
            continue
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown op kind: {op.kind!r}")
    return out


def _forward(a: Sequence[T], b: Sequence[T]) -> list[dict[int, int]]:
    """Greedy forward pass; returns the V-array snapshot for each distance d."""
    n, m = len(a), len(b)
    v: dict[int, int] = {1: 0}
    trace: list[dict[int, int]] = []
    for d in range(n + m + 1):
        trace.append(dict(v))
        for k in range(-d, d + 1, 2):
            # Down (insertion) if k == -d, or the k+1 diagonal reached
            # further than k-1; otherwise right (deletion).
            if k == -d or (k != d and v.get(k - 1, 0) < v.get(k + 1, 0)):
                x = v.get(k + 1, 0)
            else:
                x = v.get(k - 1, 0) + 1
            y = x - k
            # Follow the "snake": matching elements cost nothing.
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            v[k] = x
            if x >= n and y >= m:
                return trace
    return trace  # pragma: no cover - loop always returns


def _backtrack(trace: list[dict[int, int]], a: Sequence[T], b: Sequence[T]) -> list[Op]:
    """Walk the recorded trace backwards to recover one shortest script."""
    x, y = len(a), len(b)
    ops: list[Op] = []
    for d in range(len(trace) - 1, -1, -1):
        v = trace[d]
        k = x - y
        if k == -d or (k != d and v.get(k - 1, 0) < v.get(k + 1, 0)):
            prev_k = k + 1
        else:
            prev_k = k - 1
        prev_x = v.get(prev_k, 0)
        prev_y = prev_x - prev_k
        # Walk back along the snake of equal elements.
        while x > prev_x and y > prev_y:
            ops.append(Op("equal", x - 1, y - 1))
            x -= 1
            y -= 1
        if d == 0:
            break
        if x == prev_x:
            ops.append(Op("insert", None, y - 1))
            y -= 1
        else:
            ops.append(Op("delete", x - 1, None))
            x -= 1
    ops.reverse()
    return ops

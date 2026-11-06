"""Line diffs, word diffs and unified-diff rendering built on Myers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .myers import Op, diff

__all__ = [
    "LineChange",
    "WordChange",
    "diff_lines",
    "diff_words",
    "unified_diff",
    "render_word_diff",
]

_TOKEN_RE = re.compile(r"\S+|\s+")


@dataclass(frozen=True)
class LineChange:
    """One line of a line-level diff, in unified-diff style."""

    kind: str  # "equal" | "insert" | "delete"
    text: str


@dataclass(frozen=True)
class WordChange:
    """One token of a word-level diff."""

    kind: str  # "equal" | "insert" | "delete"
    text: str


def diff_lines(a_text: str, b_text: str) -> list[LineChange]:
    """Diff two texts line by line; returns changes in order.

    Trailing-newline handling: ``splitlines()`` is used so a missing final
    newline does not itself show up as a spurious change.
    """
    a_lines = a_text.splitlines()
    b_lines = b_text.splitlines()
    return [
        LineChange(op.kind, a_lines[op.a_index] if op.kind != "insert" else b_lines[op.b_index])  # type: ignore[index]
        for op in diff(a_lines, b_lines)
    ]


def diff_words(a_text: str, b_text: str) -> list[WordChange]:
    """Diff two texts token by token (words and whitespace runs).

    Whitespace is kept as tokens, so the diff can tell "word changed" from
    "spacing changed" and the original text can be rebuilt exactly by
    concatenating the tokens.
    """
    a_tokens = _TOKEN_RE.findall(a_text)
    b_tokens = _TOKEN_RE.findall(b_text)
    return [
        WordChange(op.kind, a_tokens[op.a_index] if op.kind != "insert" else b_tokens[op.b_index])  # type: ignore[index]
        for op in diff(a_tokens, b_tokens)
    ]


def render_word_diff(a_text: str, b_text: str) -> tuple[str, str]:
    """Render a word diff as two marked-up lines.

    Returns ``(old_rendered, new_rendered)``: deleted words are wrapped in
    ``[-...-]`` in the old text, inserted words in ``[+...+]`` in the new
    text. Equal text is untouched, so either line reads naturally.
    """
    old_parts: list[str] = []
    new_parts: list[str] = []
    run_kind: str | None = None
    run_text: list[str] = []

    def flush() -> None:
        nonlocal run_kind, run_text
        if run_kind == "delete":
            old_parts.append(f"[-{''.join(run_text)}-]")
        elif run_kind == "insert":
            new_parts.append(f"[+{''.join(run_text)}+]")
        run_kind, run_text = None, []

    for change in diff_words(a_text, b_text):
        if change.kind == "equal":
            flush()
            old_parts.append(change.text)
            new_parts.append(change.text)
        elif change.kind == run_kind:
            run_text.append(change.text)
        else:
            flush()
            run_kind = change.kind
            run_text = [change.text]
    flush()
    return "".join(old_parts), "".join(new_parts)


@dataclass
class _Hunk:
    a_start: int  # 0-based start line in a
    a_lines: list[LineChange]
    b_start: int
    b_lines: list[LineChange]


def unified_diff(
    a_text: str,
    b_text: str,
    *,
    fromfile: str = "a",
    tofile: str = "b",
    context: int = 3,
) -> str:
    """Render a GNU-style unified diff between two texts.

    Output matches ``diff -u``: a ``---``/``+++`` header, ``@@ -l,s +l,s @@``
    hunk headers (1-based, the ``,1`` omitted for single lines), and hunks
    of changed lines with ``context`` lines of surrounding context. Identical
    inputs produce an empty string.
    """
    changes = diff_lines(a_text, b_text)
    if all(c.kind == "equal" for c in changes):
        return ""

    # Group changes into hunks: a hunk is a run of non-equal lines plus up to
    # ``context`` equal lines on each side; equal runs longer than
    # ``2 * context`` split hunks.
    hunks: list[_Hunk] = []
    i = 0
    n = len(changes)
    while i < n:
        if changes[i].kind == "equal":
            i += 1
            continue
        start = max(0, i - context)
        # Walk to the end of this change run, then include trailing context.
        j = i
        last_change = i
        while j < n:
            if changes[j].kind != "equal":
                last_change = j
            elif j - last_change > 2 * context:
                break
            j += 1
        end = min(n, last_change + context + 1)
        a_start = _count_before(changes, start, "delete")
        b_start = _count_before(changes, start, "insert")
        hunk_changes = changes[start:end]
        hunks.append(
            _Hunk(
                a_start=a_start,
                a_lines=[c for c in hunk_changes if c.kind != "insert"],
                b_start=b_start,
                b_lines=[c for c in hunk_changes if c.kind != "delete"],
            )
        )
        i = end

    lines = [f"--- {fromfile}", f"+++ {tofile}"]
    for hunk in hunks:
        a_len = len(hunk.a_lines)
        b_len = len(hunk.b_lines)
        lines.append(
            f"@@ -{_fmt_range(hunk.a_start, a_len)} "
            f"+{_fmt_range(hunk.b_start, b_len)} @@"
        )
        # Re-merge a-side and b-side lines in original order.
        for change in _hunk_changes(hunk):
            prefix = {"equal": " ", "delete": "-", "insert": "+"}[change.kind]
            lines.append(f"{prefix}{change.text}")
    return "\n".join(lines) + "\n"


def _count_before(changes: list[LineChange], index: int, kind: str) -> int:
    """Number of lines in ``changes[:index]`` that exist on one side."""
    return sum(1 for c in changes[:index] if c.kind in ("equal", kind))


def _fmt_range(start: int, length: int) -> str:
    """Format a hunk range: 1-based start, ``,n`` omitted when n == 1.

    An empty range is anchored at the line *before* it, so ``start`` (the
    0-based count of lines before the hunk) is printed as-is, e.g. ``0,0``.
    """
    if length == 0:
        return f"{start},0"
    if length == 1:
        return str(start + 1)
    return f"{start + 1},{length}"


def _hunk_changes(hunk: _Hunk) -> list[LineChange]:
    """Re-interleave a hunk's a-side and b-side lines in diff order.

    The hunk stores the two sides separately (for range counting); the
    display order is recovered by re-running the diff over the hunk's own
    lines — cheap, since hunks are small.
    """
    a_texts = [c.text for c in hunk.a_lines]
    b_texts = [c.text for c in hunk.b_lines]
    return [
        LineChange(op.kind, a_texts[op.a_index] if op.kind != "insert" else b_texts[op.b_index])  # type: ignore[index]
        for op in diff(a_texts, b_texts)
    ]

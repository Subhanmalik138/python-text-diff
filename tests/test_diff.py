"""Tests for line diffs, word diffs and unified-diff rendering."""

import difflib

from textdiff.diff import diff_lines, diff_words, render_word_diff, unified_diff

A = "alpha\nbeta\ngamma\ndelta\nepsilon\nzeta\neta\ntheta\n"
B = "alpha\nbeta\ngamma\ndelta\nepsilon\nzeta\neta\ntheta\n"


def test_identical_text_has_no_diff():
    assert unified_diff(A, A) == ""
    assert diff_lines(A, A) == [
        c for c in diff_lines(A, A) if c.kind == "equal"
    ]


def test_single_line_change():
    b = A.replace("delta\n", "DELTA\n")
    out = unified_diff(A, b, fromfile="a.txt", tofile="b.txt")
    assert out.startswith("--- a.txt\n+++ b.txt\n@@ -1,7 +1,7 @@\n")
    assert "-delta\n+DELTA\n" in out


def test_matches_difflib_on_fixed_cases():
    cases = [
        ("one\ntwo\nthree\n", "one\nTWO\nthree\n"),
        ("a\nb\nc\nd\ne\nf\ng\nh\n", "a\nb\nX\nd\ne\nf\ng\nY\n"),
        ("", "first\nsecond\n"),
        ("first\nsecond\n", ""),
        ("same\n", "same\ndifferent\n"),
        ("l1\nl2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\nl10\n",
         "l1\nl2\nCHANGED\nl4\nl5\nl6\nl7\nl8\nl9\nl10\n"),
    ]
    for a, b in cases:
        expected = "".join(
            difflib.unified_diff(
                a.splitlines(keepends=True),
                b.splitlines(keepends=True),
                fromfile="a",
                tofile="b",
                n=3,
            )
        )
        assert unified_diff(a, b) == expected, f"mismatch for {a!r} -> {b!r}"


def test_hunks_split_on_long_unchanged_runs():
    a = "\n".join(f"line{i}" for i in range(20)) + "\n"
    b = a.replace("line1\n", "LINE1\n").replace("line18\n", "LINE18\n")
    out = unified_diff(a, b, context=3)
    assert sum(1 for line in out.splitlines() if line.startswith("@@")) == 2
    assert "-line1\n+LINE1\n" in out
    assert "-line18\n+LINE18\n" in out


def test_unified_diff_round_trip():
    """Applying the hunks of a unified diff to `a` must reproduce `b`."""
    import re

    def apply_unified(a_text, diff_text):
        lines = a_text.splitlines()
        out = []
        pos = 0
        for line in diff_text.splitlines():
            if line.startswith("--- ") or line.startswith("+++ "):
                continue  # file header, not a diff line
            if line.startswith("@@"):
                m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
                start = int(m.group(1))
                # Copy unchanged lines before this hunk.
                while pos < start - 1:
                    out.append(lines[pos])
                    pos += 1
            elif line.startswith(" ") or line.startswith("-"):
                if line.startswith(" "):
                    out.append(line[1:])
                pos += 1
            elif line.startswith("+"):
                out.append(line[1:])
        out.extend(lines[pos:])
        return "\n".join(out) + ("\n" if out and b.endswith("\n") else "")

    cases = [
        ("a\nb\nc\nd\ne\nf\ng\nh\n", "a\nb\nX\nd\ne\nf\ng\nY\n"),
        ("one\ntwo\nthree\n", "one\nTWO\nthree\nfour\n"),
        ("", "first\nsecond\n"),
        ("first\nsecond\n", ""),
    ]
    for a, b in cases:
        result = apply_unified(a, unified_diff(a, b))
        assert result == b, f"round-trip failed for {a!r} -> {b!r}"


def test_word_diff_marks_changes():
    old, new = render_word_diff(
        "the quick brown fox", "the fast brown fox jumps"
    )
    assert old == "the [-quick-] brown fox"
    # The space before "jumps" is itself inserted, so it sits inside the
    # insertion marker: "fox[+ jumps+]".
    assert new == "the [+fast+] brown fox[+ jumps+]"


def test_word_diff_preserves_whitespace():
    changes = diff_words("a  b\nc", "a b\nc")
    rebuilt_old = "".join(c.text for c in changes if c.kind != "insert")
    rebuilt_new = "".join(c.text for c in changes if c.kind != "delete")
    assert rebuilt_old == "a  b\nc"
    assert rebuilt_new == "a b\nc"


def test_word_diff_identical():
    assert all(c.kind == "equal" for c in diff_words("same words", "same words"))

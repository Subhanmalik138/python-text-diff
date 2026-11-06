# textdiff

A small, dependency-free Myers diff engine in Python: line diffs, word diffs,
GNU-style unified-diff output, and a `diff`-compatible CLI.

## The problem

Every version-control tool, code review UI and merge tool needs to answer
one question: *what changed between these two texts, in the fewest edits
possible?* `difflib` ships with Python but its `SequenceMatcher` is a
heuristic — it finds *a* diff, not necessarily the shortest one, and its
autojunk behaviour can silently hide real matches in repetitive text.
`textdiff` implements the classic Myers O(ND) algorithm, which guarantees a
shortest edit script, with no dependencies and no surprises.

## Design decisions

1. **Myers, not heuristics.** The greedy O(ND) algorithm from Myers (1986)
   records the furthest point reachable on each diagonal for every edit
   distance `d`, then backtracks through the trace to recover one shortest
   script. Correctness is verified in the test suite against an independent
   dynamic-programming edit distance on random inputs.
2. **Generic over sequences.** The core works on any sequence — lines,
   words, tokens, characters — so the line diff, word diff and unified-diff
   renderer all share one engine instead of three implementations.
3. **Full trace, honest trade-off.** Storing the whole trace costs O(D²)
   memory, which is the right call for source files and prose but the wrong
   one for multi-megabyte inputs; the module docstring says so plainly
   instead of pretending otherwise.
4. **Unix `diff` exit codes.** The CLI returns 0 when files match, 1 when
   they differ and 2 on error, so it drops straight into scripts and CI.

## Usage

```bash
pip install -e .

# Line diff, unified format (3 lines of context by default)
textdiff old.py new.py

# More context, coloured output
textdiff -u 5 --color old.py new.py

# Word-level diff
textdiff --words old.txt new.txt

# One file from stdin
cat new.py | textdiff old.py -
```

## Library

```python
from textdiff import diff, diff_lines, diff_words, unified_diff, edit_distance

ops = diff(["a", "b"], ["a", "c"])          # shortest edit script
print(edit_distance("kitten", "sitting"))   # 5
print(unified_diff("one\ntwo\n", "one\nTWO\n"))
old, new = render_word_diff("the quick fox", "the fast fox")
```

## Running tests

```bash
pip install pytest
python -m pytest
```

## Tech stack

- Python 3.9+ (standard library only — zero dependencies)
- pytest for tests

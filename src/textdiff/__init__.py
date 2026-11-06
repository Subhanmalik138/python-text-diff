"""textdiff — a Myers diff engine with unified-diff output and a CLI."""

from .diff import diff_lines, diff_words, render_word_diff, unified_diff
from .myers import Op, apply_to, diff, edit_distance

__all__ = [
    "Op",
    "apply_to",
    "diff",
    "diff_lines",
    "diff_words",
    "edit_distance",
    "render_word_diff",
    "unified_diff",
]

__version__ = "1.0.0"

"""Command-line interface: ``textdiff old.txt new.txt``.

Exit codes follow the Unix ``diff`` convention: 0 when the files are
identical, 1 when they differ, 2 on error (missing file, unreadable input).
"""

from __future__ import annotations

import argparse
import sys

from .diff import diff_lines, render_word_diff, unified_diff

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textdiff",
        description="Show the difference between two text files (Myers diff).",
    )
    parser.add_argument("old", help="first file (use - for stdin)")
    parser.add_argument("new", help="second file (use - for stdin)")
    parser.add_argument(
        "-u",
        "--unified",
        type=int,
        default=3,
        metavar="N",
        help="lines of context around each change (default: 3)",
    )
    parser.add_argument(
        "-w",
        "--words",
        action="store_true",
        help="diff word by word instead of line by line",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        help="colour added lines green and removed lines red",
    )
    parser.add_argument(
        "--label",
        action="append",
        default=[],
        metavar="NAME",
        help="label for the --- / +++ header (repeat twice: old, then new)",
    )
    return parser


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def _colourise(text: str) -> str:
    out = []
    for line in text.splitlines(keepends=True):
        if line.startswith("+") and not line.startswith("+++"):
            out.append(f"{GREEN}{line.rstrip(chr(10))}{RESET}\n")
        elif line.startswith("-") and not line.startswith("---"):
            out.append(f"{RED}{line.rstrip(chr(10))}{RESET}\n")
        else:
            out.append(line)
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.old == "-" and args.new == "-":
            # stdin can only be consumed once; both sides get the same text.
            old_text = new_text = sys.stdin.read()
        else:
            old_text = _read(args.old)
            new_text = _read(args.new)
    except OSError as exc:
        print(f"textdiff: {exc}", file=sys.stderr)
        return 2

    if args.words:
        old_rendered, new_rendered = render_word_diff(old_text, new_text)
        if old_text == new_text:
            return 0
        print(f"--- {args.old}")
        print(old_rendered)
        print(f"+++ {args.new}")
        print(new_rendered)
        return 1

    if old_text == new_text:
        return 0

    fromfile = args.label[0] if len(args.label) > 0 else args.old
    tofile = args.label[1] if len(args.label) > 1 else args.new
    result = unified_diff(
        old_text,
        new_text,
        fromfile=fromfile,
        tofile=tofile,
        context=args.unified,
    )
    if args.color:
        result = _colourise(result)
    sys.stdout.write(result)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Tests for the CLI: exit codes, output, word mode."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from textdiff.cli import main

SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_identical_files_exit_zero(tmp_path, capsys):
    a = write(tmp_path, "a.txt", "hello\nworld\n")
    b = write(tmp_path, "b.txt", "hello\nworld\n")
    assert main([a, b]) == 0
    assert capsys.readouterr().out == ""


def test_different_files_exit_one_and_print_unified(tmp_path, capsys):
    a = write(tmp_path, "a.txt", "hello\nworld\n")
    b = write(tmp_path, "b.txt", "hello\nthere\n")
    assert main([a, b]) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"--- {a}\n+++ {b}\n")
    assert "-world\n+there\n" in out


def test_missing_file_exit_two(tmp_path, capsys):
    assert main([str(tmp_path / "nope.txt"), str(tmp_path / "also-nope.txt")]) == 2
    assert "textdiff:" in capsys.readouterr().err


def test_word_mode(tmp_path, capsys):
    a = write(tmp_path, "a.txt", "the quick brown fox")
    b = write(tmp_path, "b.txt", "the fast brown fox")
    assert main(["--words", a, b]) == 1
    out = capsys.readouterr().out
    assert "[-quick-]" in out
    assert "[+fast+]" in out


def test_stdin(tmp_path):
    env = {**os.environ, "PYTHONPATH": SRC_DIR}
    proc = subprocess.run(
        [sys.executable, "-m", "textdiff.cli", "-", "-"],
        input="same\n",
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
    )
    assert proc.returncode == 0

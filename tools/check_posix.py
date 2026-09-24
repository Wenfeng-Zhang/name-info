#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Run the suite with ``os.path`` swapped for ``posixpath``.

    python tools/check_posix.py

Development happens on Windows, so a test that quietly relies on ``ntpath``
behaviour only fails once CI reaches Linux or macOS — which is exactly how
``test_one_sequence_many_spellings`` slipped through. This script swaps
``os.path`` inside the ``name_info.name_info`` module for ``posixpath`` and runs
the suite, reproducing most such failures locally in a second.

Run it before pushing any change that touches paths, tests or fixtures.

It is a heuristic, not a substitute for CI: only path semantics change. Real
differences in file systems, permissions, line endings or the interpreter
itself are not covered. ``PlatformPathTests`` and ``CommandLineTests`` are
skipped on purpose — the former asserts the *current* platform, and the latter
spawns a real subprocess, so the swap would only confuse them.
"""

import os
import posixpath
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

SUITE = (
    "test_name_info.SnapshotTests",
    "test_name_info.NameInfoTests",
    "test_name_info.DocumentationTests",
)


class PosixOs(object):
    """``os`` with only its ``path`` module replaced."""

    path = posixpath

    def __getattr__(self, name):
        return getattr(os, name)


def main():
    import name_info.name_info as implementation

    original = implementation.os
    implementation.os = PosixOs()
    try:
        suite = unittest.TestLoader().loadTestsFromNames(SUITE)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        implementation.os = original

    print()
    print("posix-simulated run: {0} tests, {1} failure(s), {2} error(s)".format(
        suite.countTestCases(), len(result.failures), len(result.errors)))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

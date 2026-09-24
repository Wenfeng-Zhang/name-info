#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Check the suite against POSIX path semantics without leaving Windows.

    python tools/check_posix.py

Development happens on Windows, so a test that quietly relies on ``ntpath``
behaviour only fails once CI reaches Linux or macOS. Two checks run here:

1. the test suite, with ``os.path`` inside ``name_info.name_info`` swapped for
   ``posixpath``;
2. a cross-platform contract check over every recorded input (examples, edge
   cases and the matrix): the path *head* — ``dirname`` — is allowed to differ
   between the two flavours, while everything from ``basename`` onwards must be
   byte-identical.

Run it before pushing any change that touches paths, tests or fixtures. It is a
heuristic, not a substitute for CI: only path semantics change here, so file
systems, permissions, line endings and interpreter differences remain covered by
CI alone.
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

# The path head is platform specific; every other field must be portable.
PLATFORM_FIELD = "dirname"


class PosixOs(object):
    """``os`` with only its ``path`` module replaced."""

    path = posixpath

    def __getattr__(self, name):
        return getattr(os, name)


def contract_check(implementation):
    """Compare every recorded input under both path flavours."""
    import test_name_info

    inputs = list(test_name_info.file_names)
    inputs.extend(test_name_info.edge_cases())
    inputs.extend(test_name_info.matrix_cases())

    real_os = implementation.os
    try:
        windows = {name: test_name_info.snapshot(name) for name in inputs}
        implementation.os = PosixOs()
        posix = {name: test_name_info.snapshot(name) for name in inputs}
    finally:
        implementation.os = real_os

    differences = []
    for name in inputs:
        for field, value in windows[name].items():
            if field == PLATFORM_FIELD:
                continue
            if value != posix[name][field]:
                differences.append((name, field, value, posix[name][field]))

    print()
    print("cross-platform contract over {0} inputs".format(len(inputs)))
    if differences:
        print("  {0} difference(s) outside {1!r}:".format(
            len(differences), PLATFORM_FIELD))
        for name, field, windows_value, posix_value in differences[:20]:
            print("    {0}\n      windows {1}={2!r}\n      posix   {1}={3!r}".format(
                name, field, windows_value, posix_value))
    else:
        print("  ok: only {0!r} differs between windows and posix".format(
            PLATFORM_FIELD))
    return not differences


def main():
    import name_info.name_info as implementation

    real_os = implementation.os
    implementation.os = PosixOs()
    try:
        suite = unittest.TestLoader().loadTestsFromNames(SUITE)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    finally:
        implementation.os = real_os

    print()
    print("posix-simulated suite: {0} tests, {1} failure(s), {2} error(s)".format(
        suite.countTestCases(), len(result.failures), len(result.errors)))

    contract_ok = contract_check(implementation)

    if result.wasSuccessful() and contract_ok:
        print("all checks passed")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

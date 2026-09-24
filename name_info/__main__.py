#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Entry point of ``python -m name_info``.

Without arguments it prints the parse result of every example in
``name_info.examples.file_names``; pass file names or paths to check arbitrary
naming instead.
"""

import argparse

from .examples import file_names
from .name_info import NameInfo


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m name_info",
        description="Parse file names or sequence paths and print the NameInfo attributes.",
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        help="file names or paths to parse; without arguments the built-in examples are used",
    )
    return parser


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    for filename in arguments.filenames or file_names:
        print(filename)
        info = NameInfo(filename)
        print(info)
        print('\t')


if __name__ == "__main__":
    main()

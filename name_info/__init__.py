#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""name_info package: exposes ``NameInfo``.

The implementation lives in the same-named ``name_info.name_info`` module, and the
demo / snapshot inputs in ``name_info.examples`` (deliberately outside the public
API), so ``from name_info import NameInfo`` stays the only recommended import.
"""

from .name_info import NameInfo

__version__ = "0.1.0"

__all__ = ["NameInfo"]

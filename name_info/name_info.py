#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Core implementation of the file name / sequence parser.

    info = NameInfo("shot.1001.exr")
    info.name       # "shot."
    info.absname    # "shot"
    info.wild_name  # "shot.????"
    info.template   # "shot.%04d.exr"

``python -m name_info`` parses arbitrary paths and falls back to the built-in
examples when it is called without arguments.

Time        :   2025/12/31
Author      :   Wenfeng Zhang
Email       :   zwf.vfx@foxmail.com
"""

import os
import re


class NameInfo:
    """Parse a file name into sequence information; the file system is never touched.

    ``filename`` is the normalized input path, and ``basename`` / ``dirname`` come
    from ``os.path.split``. ``name`` is the stem with the main pattern removed,
    ``absname`` is ``name`` without trailing dots. ``pattern`` is the matched
    pattern, ``padding`` its declared width and ``ext`` the extension without the
    leading dot. ``wild_name`` is the extension-less wildcard stem and
    ``template`` the full path template. ``other_pattern`` records a second
    pattern (UV tile, view or frame) when one coexists with the main pattern.

    Attributes stay writable, and ``template`` is recomputed from the current
    attributes on every access.

    Two details are easy to trip over:

    * ``pattern is None`` means the input has no extension and was not parsed at
      all, while ``pattern == ''`` means it was parsed but no pattern applies.
    * ``padding == 0`` covers both "no declared width" (``%d``, ``$F``) and UV
      tiles (``u1_v1``), whose digit counts live in ``wild_name`` instead.
    """

    # __slots__ keeps instances small, which matters when parsing many files.
    __slots__ = ('filename', 'basename', 'dirname', 'name', 'pattern', 'ext',
                 'absname', 'padding', 'wild_name', 'other_pattern')

    # Image formats.
    _IMG_EXTS = {'.exr', '.dpx', '.tiff', '.tif', '.png', '.jpg', '.jpeg', '.bmp', '.tga', '.cin', '.iff', '.psd', '.rat'}
    # Geometry and cache formats.
    _GEO_EXTS = {'.vdb', '.abc', '.usd', '.usda', '.usdc', '.usdz', '.obj', '.fbx', '.ass', '.rs', '.rib'}

    # Union of both sets: the extensions that may be stripped from a ".tx" name.
    KNOWN_EXTS = _IMG_EXTS | _GEO_EXTS

    # Compound suffixes that must be treated as one extension, so that the inner
    # part does not leak into "name".
    SPECIAL_FORMATS = ['.bgeo.sc', '.bgeo.gz', '.ass.gz', '.vdb.sc', '.vdb.gz',
                       '.tar.gz', '.exr.gz', '.exr.bak']

    # Video files are not frame sequences, so they skip pattern detection.
    # Values carry no leading dot, matching the normalized result of _split_ext.
    VIDEO_EXTS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

    # Explicit placeholders have the highest priority: printf style (%04d),
    # Houdini style ($F4), "#", <UDIM>, %(UDIM)d and u<U>_v<V>.
    RE_PLACEHOLDER = re.compile(r'%\d*d|#+|<UDIM>|%\(UDIM\)d|u<U>_v<V>|\$F\d*', re.IGNORECASE)
    # Standalone four-digit frame numbers, the VFX default. The lookarounds keep
    # the run independent and require nothing but non-digits (or a "(digits)"
    # suffix) after it; (?<![vV]) keeps version numbers such as v1001 out.
    RE_FOUR_DIGITS = re.compile(r'(?<![vV])(?<!\d)(\d{4})(?!\d)(?=[^\d]*$|[^\d]*\(\d+\))', re.IGNORECASE)
    # UV tiles ("u1_v1", "u10_v1"), the common multi-quadrant texture naming.
    RE_UV_TILE = re.compile(r'u(\d+)_v(\d+)', re.IGNORECASE)
    RE_UV_PLACEHOLDER = re.compile(r'u<U>_v<V>', re.IGNORECASE)
    # View tokens (%V, %v); only ever recorded as a secondary pattern.
    RE_VIEW_PLACEHOLDER = re.compile(r'%[vV]')
    # Frame placeholders, excluding the UDIM and UV forms covered above.
    RE_FRAME_PLACEHOLDER = re.compile(r'%\d*d|#+|\$F\d*', re.IGNORECASE)
    # Last-resort numeric match.
    RE_NUMBER = re.compile(r'\d+')
    # Trailing version token such as "v001"; used to exclude non-frame numbers.
    RE_VERSION_END = re.compile(r'(?<!u\d_)v\d+$', re.IGNORECASE)
    # Any version token in the stem; such tokens are skipped by rule 5.
    RE_VERSION_TOKEN = re.compile(r'(?<![A-Za-z0-9])v\d+(?=$|[._-])', re.IGNORECASE)
    # Point-separated digits right before a trailing version token, e.g. the
    # "1001" in "plate.1001.v002"; underscore-separated shot numbers do not count.
    RE_FRAME_BEFORE_VERSION = re.compile(r'(?<!\d)(\d+)(?=\.v\d+$)', re.IGNORECASE)
    # "<dot><digits>" at the end of the stem; makes rule 3.1 skip UV tiles.
    RE_DOT_NUMBER_END = re.compile(r'\.\d+$')

    # Helpers: the declared padding ($F4, %04d) and the leading-1 prefix that
    # marks a likely frame number ("10001" and longer still match the prefix).
    RE_PADDING = re.compile(r'\$F(\d*)|%(\d*)d', re.IGNORECASE)
    RE_THOUSANDS = re.compile(r'1\d{3}')
    # Padding widths above this raise ValueError.
    MAX_PADDING = 256

    def __init__(self, filename: str):
        # Normalize first: mixed separators and surrounding whitespace never
        # reach the parser.
        self.filename = filename.strip().replace('\\', '/')
        self.dirname, self.basename = os.path.split(self.filename)

        self.name = None           # stem with the main pattern removed
        self.pattern = None        # matched pattern, e.g. "%04d" or "1001"
        self.ext = None            # extension without the leading dot
        self.absname = None        # name without trailing dots, not an absolute path
        self.padding = 0           # declared padding width, 0 when unspecified
        self.wild_name = None      # extension-less wildcard stem, e.g. "file.????"
        self.other_pattern = None  # second pattern, e.g. UV tile / view / frame

        self._parse()

    @property
    def template(self):
        """Full path template, recomputed from the current attributes.

        For example ``D:/Project/shot.1001.exr`` becomes
        ``D:/Project/shot.%04d.exr``, which is what you want to store in a database
        or hand to a renderer. Returns ``filename`` unchanged when there is no
        pattern or no padding. The property is read-only; change ``pattern`` or
        ``padding`` instead.
        """
        if not self.padding or not self.pattern:
            return self.filename

        # Keep the original case of the placeholder; only UDIM is normalized.
        if self.pattern.upper() in ('<UDIM>', '%(UDIM)D'):
            fmt = '<UDIM>'
        elif self.pattern.isdigit():
            fmt = f'%0{self.padding}d'
        else:
            # Other placeholders ($F4, u<U>_v<V>, ...) are kept as written.
            fmt = self.pattern

        # Replace inside the stem only, so a pattern that also matches the
        # extension cannot be replaced in the wrong place.
        stem, _ = self._split_ext()
        suffix = self.basename[len(stem):]
        new_basename = fmt.join(stem.rsplit(self.pattern, 1)) + suffix

        if not self.dirname:
            return new_basename
        separator = '' if self.dirname.endswith('/') else '/'
        return f"{self.dirname}{separator}{new_basename}"

    def _parse(self):
        """Run the whole parse in one pass; called once from __init__."""
        # Extensions: compound suffixes (.bgeo.sc) and ".tx" caches included.
        stem, ext = self._split_ext()
        self.ext = ext
        # No extension means there is nothing to parse.
        if not ext:
            return

        # Videos are never treated as sequences.
        if ext.lower() in self.VIDEO_EXTS:
            name = stem
            pattern = ''
        else:
            name, pattern = self._find_pattern(stem)

        # Derive the declared width and the wildcard stem from the pattern.
        if pattern:
            padding = self._padding_width(pattern)
            wild_name = self._wildcard(stem, pattern, padding)
        else:
            padding, wild_name = 0, name

        self.name = name
        self.pattern = pattern
        self.absname = name.rstrip('.')
        self.padding = padding
        self.wild_name = wild_name
        self.other_pattern = self._find_other_pattern(stem, pattern)

    def _split_ext(self):
        """Split ``basename`` into (stem, ext).

        ``ext`` has no leading dot and is lower-cased; it may contain two layers
        ("exr.gz") and is ``''`` when the name has no extension. For ".tx" caches a
        known inner extension is stripped as well, so ``shot.1001.exr.tx`` yields
        ``("shot.1001", "tx")``.
        """
        basename = self.basename
        lower_basename = basename.lower()

        for fmt in self.SPECIAL_FORMATS:
            if lower_basename.endswith(fmt):
                return basename[:-len(fmt)], fmt.lstrip('.')

        # ".tx" texture caches: strip the inner extension when it is a known one.
        if lower_basename.endswith('.tx'):
            inner_stem, inner_ext = os.path.splitext(basename[:-3])
            if inner_ext.lower() in self.KNOWN_EXTS:
                return inner_stem, 'tx'
            return basename[:-3], 'tx'

        if '.' not in basename:
            return basename, ''

        stem, ext = os.path.splitext(basename)
        return stem, ext.lstrip('.').lower()

    def _find_pattern(self, stem: str):
        """Return (name, pattern), applying the rules in this order:

        1. explicit placeholder, 2. standalone four-digit number, 3. heuristics
        (UV tile, then version handling, then any number). ``pattern`` is ``''``
        when nothing matched, and ``name`` is then the untouched stem, i.e. a
        static file name.
        """
        # 1. Explicit placeholders (%04d, ####, <UDIM>, ...).
        match = self.RE_PLACEHOLDER.search(stem)
        if match:
            pattern = match.group(0)
            return self._strip_pattern(stem, pattern), pattern

        # 2. Standalone four-digit frame number, e.g. ".1001.".
        match = self.RE_FOUR_DIGITS.search(stem)
        if match:
            pattern = match.group(0)
            return self._strip_pattern(stem, pattern), pattern

        # 3. Heuristics.

        # 3.1 UV tiles come before the version check, so multi-digit coordinates
        #     such as u10_v1 still match.
        match_uv = self.RE_UV_TILE.search(stem)
        if match_uv and not self.RE_DOT_NUMBER_END.search(stem):
            pattern = match_uv.group(0)
            return self._strip_pattern(stem, pattern), pattern

        # 3.2 A trailing version token: keep the point-separated digits directly
        #     before it, otherwise the name has no frame at all.
        version = self.RE_VERSION_END.search(stem)
        if version:
            frame = self.RE_FRAME_BEFORE_VERSION.search(stem)
            if frame:
                pattern = frame.group(1)
                return self._strip_pattern(stem, pattern), pattern
            return stem, ''

        # 3.3 Any number: the first one matching the "1xxx" prefix wins,
        #     otherwise the last one. A single pass avoids building both the full
        #     match list and the filtered one.
        versions = list(self.RE_VERSION_TOKEN.finditer(stem))
        pattern = ''
        for match in self.RE_NUMBER.finditer(stem):
            if any(v.start() <= match.start() < v.end() for v in versions):
                continue
            pattern = match.group(0)
            if self.RE_THOUSANDS.match(pattern):
                break
        if not pattern:
            # No digits at all: a static file name.
            return stem, ''

        return self._strip_pattern(stem, pattern), pattern

    def _find_other_pattern(self, stem: str, pattern: str):
        """Record the second pattern (UV tile, view or frame) when one coexists."""
        if not pattern:
            return None
        if self.RE_UV_TILE.fullmatch(pattern) or self.RE_UV_PLACEHOLDER.fullmatch(pattern):
            frame = self.RE_FRAME_PLACEHOLDER.search(stem) or self.RE_FOUR_DIGITS.search(stem)
            return frame.group(0) if frame else None
        for regex in (self.RE_UV_TILE, self.RE_UV_PLACEHOLDER, self.RE_VIEW_PLACEHOLDER):
            match = regex.search(stem)
            if match:
                return match.group(0)
        return None

    def _strip_pattern(self, stem: str, pattern: str):
        """Remove ``pattern`` and keep one adjacent delimiter.

        ``leg_02_1021_Height`` becomes ``leg_02_Height``: the delimiter attached to
        the pattern is kept, and an underscore is inserted when neither side has
        one.
        """
        if stem.endswith(pattern):
            return stem[:-len(pattern)]
        prefix, suffix = stem.rsplit(pattern, 1)
        if prefix.endswith(('.', '_', '-')):
            return prefix + suffix.lstrip('._-')
        if suffix.startswith(('.', '_', '-')):
            return prefix + suffix
        return prefix + '_' + suffix

    def _padding_width(self, pattern: str):
        """Return the declared padding width, or 0 when the pattern declares none.

        ``<UDIM>`` is 4, runs of ``#`` and literal digits use their length,
        ``%04d`` / ``$F4`` use the declared number, and ``%d`` / ``$F`` and UV
        tiles are 0. Widths above ``MAX_PADDING`` raise ``ValueError``.
        """
        if pattern.upper() in ['<UDIM>', '%(UDIM)D']:
            padding = 4
        elif pattern.startswith('#') or pattern.isdigit():
            padding = len(pattern)
        else:
            match = self.RE_PADDING.search(pattern)
            num_str = (match.group(1) or match.group(2)) if match else ''
            padding = int(num_str) if num_str else 0
        if padding > self.MAX_PADDING:
            raise ValueError(f"pattern width exceeds {self.MAX_PADDING}")
        return padding

    def _wildcard(self, stem: str, pattern: str, padding: int):
        """Build the extension-less wildcard stem, e.g. ``shot.????``.

        A declared padding turns the pattern into that many question marks; UV
        placeholders and UV tiles are handled separately so that every coordinate
        keeps its own digit count and case.
        """
        if padding:
            parts = stem.rsplit(pattern, 1)
            return ('?' * padding).join(parts)
        if self.RE_UV_PLACEHOLDER.fullmatch(pattern):
            # Every occurrence is replaced, not only the last one.
            return stem.replace(pattern, '{}?_{}?'.format(pattern[0], pattern[5]))
        match_uv = self.RE_UV_TILE.match(pattern)
        if match_uv:
            # One question mark per digit, so u10 and u1 do not share a wildcard.
            u_val, v_val = match_uv.groups()
            temp = (pattern[:match_uv.start(1)] + '?' * len(u_val)
                    + pattern[match_uv.end(1):match_uv.start(2)]
                    + '?' * len(v_val) + pattern[match_uv.end(2):])
            parts = stem.rsplit(pattern, 1)
            return temp.join(parts)
        return stem

    def __repr__(self):
        # Unparsed input (no extension) has nothing to show.
        if self.name is None:
            return ""
        s = "name='{0}', pattern='{1}', ext='{2}', absname='{3}', padding={4}, wild_name='{5}'"
        return s.format(self.name, self.pattern, self.ext, self.absname, self.padding, self.wild_name)

    def __str__(self):
        return self.__repr__()

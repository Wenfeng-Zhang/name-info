# Parsing rules

This document describes exactly what `NameInfo` does, in the order the code does
it. It is the reference behind the snapshot tests in
`tests/fixtures/snapshot.json`.

## 1. Path normalization

`__init__` first runs

```python
filename = input.strip().replace("\\", "/")
dirname, basename = os.path.split(filename)
```

so mixed separators and surrounding whitespace never reach the parser.

`dirname` comes from `os.path`, so the **path head is platform specific** — that
is expected, not a defect: Linux and macOS report their own form rather than a
Windows one. Everything from `basename` onwards stays portable.
`PlatformPathTests` pins the three shapes where the head differs:

* **Drive-relative paths** — `os.path.split("D:shot.1001.exr")` gives
  `("D:", "shot.1001.exr")` on Windows but `("", "D:shot.1001.exr")` on POSIX.
  Here even `basename` differs, so `name`, `absname`, `wild_name` and `template`
  differ with it; such an input cannot join the cross-platform contract.
* **Files directly in a drive root** — `os.path.split("D:/a.1001.exr")` gives
  `dirname` `"D:/"` on Windows but `"D:"` on POSIX. Only `dirname` differs;
  `basename`, `absname`, `padding` and `template` are identical.
* **UNC paths** — `ntpath` keeps the trailing slash of `//server/share/`,
  `posixpath` drops it. Again only `dirname` differs.

The snapshot fixture therefore treats `dirname` as platform specific but
spelling-independent: trailing slashes are stripped before comparing, so `D:/`
and `D:` count as equal, while every other field must match byte for byte. The
exact head is pinned per platform in `PlatformPathTests`, and
`tools/check_posix.py` asserts that nothing else differs across all recorded
inputs. When you need a key to group files across platforms,
use `absname` + `ext` rather than a raw `dirname` string.

## 2. Extension resolution (`_split_ext`)

Tried in this order, case-insensitively:

1. **Compound suffixes** — if the name ends with one of `.bgeo.sc`, `.bgeo.gz`,
   `.ass.gz`, `.vdb.sc`, `.vdb.gz`, `.tar.gz`, `.exr.gz`, `.exr.bak`, that whole
   suffix becomes `ext` (without the leading dot, e.g. `exr.gz`).
2. **`.tx` caches** — with `.tx` removed, if the remaining extension is in
   `KNOWN_EXTS`, that inner extension is stripped as well and `ext` becomes
   `tx`. `shot.1001.exr.tx` therefore yields stem `shot.1001` and `ext='tx'`.
   `shot.1001.foo.tx` keeps `foo` (it is not a known image format).
3. **No dot** — `ext` is `''` and parsing stops immediately: `name`, `pattern`,
   `absname` and `wild_name` stay `None`.
4. **Otherwise** — plain `os.path.splitext`, lower-cased, without the dot.

`ext` is always lower-case; `filename`/`basename` keep their original case.

Two dot conventions coexist on purpose:

- `_IMG_EXTS`, `_GEO_EXTS`, `KNOWN_EXTS`, `SPECIAL_FORMATS` hold values **with**
  a leading dot, because they are compared against `os.path.splitext` output.
- `VIDEO_EXTS` holds values **without** a dot, because it is compared against the
  normalized `ext`.

## 3. Pattern detection (`_find_pattern`)

`RE_PLACEHOLDER` / `RE_FOUR_DIGITS` / `RE_UV_TILE` / `RE_UV_PLACEHOLDER` /
`RE_VIEW_PLACEHOLDER` / `RE_FRAME_PLACEHOLDER` / `RE_NUMBER` / `RE_VERSION_END` /
`RE_VERSION_TOKEN` / `RE_FRAME_BEFORE_VERSION` / `RE_DOT_NUMBER_END` are the
class-level patterns; `RE_PADDING` and `RE_THOUSANDS` are helpers.

| Priority | Condition | Result |
| --- | --- | --- |
| 1 | `RE_PLACEHOLDER` matches `%\d*d`, `#+`, `<UDIM>`, `%(UDIM)d`, `u<U>_v<V>`, `$F\d*` | that substring is the pattern |
| 2 | `RE_FOUR_DIGITS` matches a standalone four-digit run that is followed by no further digits up to the end, or by `(<digits>)` | that four-digit run is the pattern |
| 3 | `RE_UV_TILE` matches `u(\d+)_v(\d+)` and the stem does *not* end with `.<digits>` | `u10_v1` style match is the pattern |
| 4 | `RE_VERSION_END` matches a trailing `v\d+` | the digits right before it (`\d+(?=\.v\d+$)`) become the pattern, otherwise no pattern |
| 5 | any number, skipping `v\d+` tokens | the first number matching `1\d{3}` wins, else the last number |

If no number is found at all the input is treated as a static file name:
`pattern == ''` and `name == stem`.

## 4. Removing the pattern (`_strip_pattern`)

The pattern is removed at its **last** occurrence, keeping one adjacent
delimiter so that `leg_02_1021_Height.tif` becomes `leg_02_Height`:

| Shape of the split | Result |
| --- | --- |
| pattern at the end | the prefix, unchanged |
| prefix ends with `.`, `_` or `-` | `prefix + suffix.lstrip("._-")` |
| suffix starts with `.`, `_` or `-` | `prefix + suffix` |
| neither | `prefix + "_" + suffix` |

`absname` is `name.rstrip(".")`.

## 5. Padding and wildcards

`_padding_width(pattern)` returns the declared width:

| Pattern | `padding` |
| --- | --- |
| `<UDIM>`, `%(UDIM)d` (any case) | 4 |
| `#`, `##`, `####` | length of the run |
| literal digits (`1001`, `10001`) | length of the digits |
| `%04d`, `$F4` | the declared number |
| `%d`, `$F` | 0 |
| UV tiles (`u10_v1`) | 0 |

Widths above `MAX_PADDING` (256) raise `ValueError`.

`_wildcard(stem, pattern, padding)` then builds `wild_name`, which never
contains the extension:

- with a non-zero padding: `pattern` is replaced by `?` × `padding` (last
  occurrence only) → `shot.????`
- `u<U>_v<V>`: every occurrence is replaced by `u?_v?`, preserving case →
  `a_u?_v?_b_u?_v?`
- UV tiles: one `?` per digit of each coordinate, preserving case →
  `u10_v1` becomes `u??_v?`
- otherwise (width-less placeholders such as `%d`): the stem is returned
  unchanged

## 6. Template

`template` is a property, recomputed from the current attributes on every
access. With no pattern or no padding it returns `filename` unchanged, so a
static name round-trips. Otherwise:

- `<UDIM>` / `%(UDIM)d` normalize to `<UDIM>` (any case)
- literal digits become `%0Nd` with `N == padding`
- other placeholders (`$F4`, `%04d`, `u<U>_v<V>`) are kept as written

Only the last occurrence inside the stem is replaced, and the extension part is
kept verbatim, so `shot.1001.TIF.TX` yields `shot.%04d.TIF.TX`.

## 7. Video files

If `ext` is in `VIDEO_EXTS`, no pattern detection happens at all: `name` is the
stem, `pattern` is `''`, and `template` returns `filename`.

## 8. Known limits

These are deliberate consequences of the heuristics, all covered by the
snapshot tests.

- `$F\d*` matches a bare `$F`, so `cache_$Frame.exr` parses as pattern `$F` and
  `name == 'cache_rame'`. The same applies to `$Foo`.
- `%\d*d` matches `%d` inside ordinary words: `pct_100%discount.exr` gives
  pattern `%d` and `name == 'pct_100_iscount'`.
- `#+` matches any `#`, so `note_10#_v1.exr` gets pattern `#`.
- Because the four-digit rule only fires when nothing but non-digits follows,
  `plate_1001_2001.exr` picks the **last** qualifying number (`2001`), while
  `a_1001_b_1002_8k.exr` falls through to rule 5 and picks `1001`.
- `padding == 0` is overloaded: it means "no declared width" for `%d`/`$F` and
  "UV tile" for `u1_v1`. The width information for UV tiles lives in
  `wild_name`.
- `pattern is None` (unparsed, no extension) and `pattern == ''` (parsed, no
  pattern) are different states and should be checked with `is None` when it
  matters.
- Only one inner extension layer is stripped for `.tx`.

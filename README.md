**English** | [中文](README.zh-CN.md)

[![tests](https://github.com/Wenfeng-Zhang/name-info/actions/workflows/tests.yml/badge.svg)](https://github.com/Wenfeng-Zhang/name-info/actions/workflows/tests.yml)
[![python](https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://github.com/Wenfeng-Zhang/name-info/blob/main/pyproject.toml)
[![platforms](https://img.shields.io/badge/platforms-linux%20%7C%20windows%20%7C%20macos-lightgrey)](https://github.com/Wenfeng-Zhang/name-info/actions/workflows/tests.yml)
[![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](https://github.com/Wenfeng-Zhang/name-info/blob/main/pyproject.toml)
[![license](https://img.shields.io/github/license/Wenfeng-Zhang/name-info)](LICENSE)

# name-info

Parse VFX file names and frame sequences into structured information.

`NameInfo` takes a file name (or a full path) and works out where the frame
pattern is, what the extension is, and how to rewrite the path back into a
sequence template. It never touches the file system, so it is safe to run on
paths that do not exist yet.

## Why: one sequence, many spellings

The same sequence reaches you under several spellings, depending on who wrote it:

| Spelling | Where it comes from |
| --- | --- |
| `d:/render/a.1001.exr` | a frame a renderer actually wrote to disk |
| `d:/render/a.%04d.exr` | the printf template stored in a database |
| `d:/render/a.####.exr` | Houdini's frame token |

Compared as plain strings these look like three different things — which is how
copying, renaming or handing them to a renderer goes wrong. `name_info` parses
every spelling into the same sequence identity:

```python
from name_info import NameInfo

spellings = ["d:/render/a.%04d.exr", "d:/render/a.####.exr", "d:/render/a.1001.exr"]

for path in spellings:
    info = NameInfo(path)
    print(info.pattern, "->", info.absname, info.padding, info.wild_name)
# %04d -> a 4 a.????
# #### -> a 4 a.????
# 1001 -> a 4 a.????

# One key per sequence; the spelling is deliberately not part of it.
keys = {(i.dirname, i.absname, i.ext) for i in map(NameInfo, spellings)}
assert keys == {("d:/render", "a", "exr")}     # all three are the same sequence
```

`pattern` records *how* the sequence was written, so it differs on purpose.
Everything that says *which* sequence it is — `dirname`, `absname`, `padding`,
`ext`, `wild_name` — comes out identical. Those are the fields to sort, group,
compare and cache on before copying files around or feeding a renderer.

One caveat: `template` keeps the spelling it found, so `####` stays
`d:/render/a.####.exr` while `1001` becomes `d:/render/a.%04d.exr`. When a whole sequence needs
one canonical template, build it from `absname`, `padding` and `ext` rather than
taking the first `template` you happen to see.

## Quick start

```python
from name_info import NameInfo

info = NameInfo("d:/render/shot.1001.exr")

info.name        # 'shot.'
info.absname     # 'shot'
info.pattern     # '1001'
info.padding     # 4
info.ext         # 'exr'
info.wild_name   # 'shot.????'
info.template    # 'd:/render/shot.%04d.exr'
```

中文说明见 [README.zh-CN.md](README.zh-CN.md)。

## Features

- Explicit placeholders: `%04d`, `%d`, `####`, `$F4`, `<UDIM>`, `%(UDIM)d`,
  `u<U>_v<V>`
- VFX-style four-digit frame numbers such as `shot.1001.exr`
- UV tiles (`u1_v1`, `u10_v1`) and view tokens (`%V`, `%v`)
- Version tokens (`v001`, `v0028`) are excluded from frame detection
- Compound extensions: `.exr.gz`, `.exr.bak`, `.bgeo.sc`, `.ass.gz`, `.tar.gz`
- `.tx` texture caches (`.exr.tx` keeps `tx` as the extension)
- Video formats bypass sequence detection: `mp4`, `mov`, `avi`, `mkv`, `webm`
- Zero runtime dependencies, `__slots__` keeps instances small

## Requirements

- Python 3.7 or newer (3.7, 3.9, 3.10 and 3.11 are covered by the test matrix)
- Python 2 is **not** supported: the code uses type hints and f-strings

## Installation

```console
python -m pip install .
```

Editable install for development (needs `setuptools >= 61`):

```console
python -m pip install -e .
```

The test suite needs no third-party packages, so it runs straight from a clone
without installing anything.

## Attributes

| Attribute | Example for `d:/render/shot.1001.exr` | Meaning |
| --- | --- | --- |
| `filename` | `'d:/render/shot.1001.exr'` | Input path, backslashes normalized to `/`, whitespace stripped |
| `dirname` | `'d:/render'` | Directory part of `filename` |
| `basename` | `'shot.1001.exr'` | File name part of `filename` |
| `name` | `'shot.'` | Stem with the main pattern removed, keeping the adjacent delimiter |
| `absname` | `'shot'` | `name` with trailing dots stripped |
| `pattern` | `'1001'` | Matched pattern: literal digits, or the placeholder itself |
| `padding` | `4` | Declared padding width, `0` when unspecified |
| `ext` | `'exr'` | Extension without the leading dot, possibly compound |
| `wild_name` | `'shot.????'` | Wildcard stem (no extension), `?` per digit |
| `other_pattern` | `None` | The second pattern found (UV tile / view / frame), else `None` |
| `template` | `'d:/render/shot.%04d.exr'` | Path template, recomputed on every access |

All attributes stay writable, and `template` is derived from the current
attributes, so it follows manual edits:

```python
info.padding = 6
info.template    # 'd:/render/shot.%06d.exr'
```

Notes:

- `pattern is None` means the input has no extension and was not parsed at all.
  `pattern == ''` means it was parsed but no sequence pattern applies.
- `padding` is `0` both for placeholders without a width (`%d`, `$F`) and for UV
  tiles, whose widths are encoded in `wild_name` instead.

## Parsing order

| Priority | Rule | Example |
| --- | --- | --- |
| 1 | Explicit placeholder | `shot.%04d.exr`, `leg_02_<UDIM>_Height.tif`, `shot.$F4.exr` |
| 2 | Four-digit number at the end of the stem | `shot.1001.exr` |
| 3 | UV tile (skipped when the stem ends with `.<digits>`) | `tex_u10_v1.exr` |
| 4 | Version token handling | `shot.1001.exr` from `shot.v0028.1001.exr` |
| 5 | Any number, preferring one starting with `1` | `asset_10001_8k.exr` |

More detail, including the regular expressions and known edge cases, is in
[docs/parsing-rules.md](docs/parsing-rules.md).

## Command line

Without arguments it prints the parsing result of every input in
`name_info.examples.file_names`; pass your own names to check any path:

```console
python -m name_info
python -m name_info shot.1001.exr d:/render/plate.%04d.exr
python -m name_info --help
```

```text
shot.1001.exr
name='shot.', pattern='1001', ext='exr', absname='shot', padding=4, wild_name='shot.????'

...
```

## Examples

[`docs/examples.md`](docs/examples.md) expands the same output, grouped by feature
(placeholders, UDIM, UV tiles, four-digit frames, versions, textures, videos) with
the real output next to every input. A taste:

```text
d:/render/testA_diffuse.%04d.exr
name='testA_diffuse.', pattern='%04d', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse.????'

d:/render/shot.1001.1001.ext
name='shot.1001.', pattern='1001', ext='ext', absname='shot.1001', padding=4, wild_name='shot.1001.????'

d:/tex/testA_u10_v1.exr
name='testA_', pattern='u10_v1', ext='exr', absname='testA_', padding=0, wild_name='testA_u??_v?'

d:/tex/testA_leg_02_1021_Height.tif
name='testA_leg_02_Height', pattern='1021', ext='tif', absname='testA_leg_02_Height', padding=4, wild_name='testA_leg_02_????_Height'

d:/render/testA2_Bokeh_DOF_04.mp4
name='testA2_Bokeh_DOF_04', pattern='', ext='mp4', absname='testA2_Bokeh_DOF_04', padding=0, wild_name='testA2_Bokeh_DOF_04'

d:/render/testA
```

The last input has no extension, so nothing is parsed and its output is empty.

## Tests

The suite only needs the standard library. From the project root:

```console
python -m unittest discover
```

These forms are equivalent:

```console
python -m unittest discover -s tests
python tests/test_name_info.py
```

`tests/test_name_info.py` inserts the project root into `sys.path` itself, so
neither an installation nor a `PYTHONPATH` is required.

Run the full interpreter matrix (creates `.venv37`, `.venv39`, `.venv310`,
`.venv311` next to the sources and runs the suite in each):

```powershell
powershell -ExecutionPolicy Bypass -File tools/run_matrix.ps1
```

Before pushing anything that touches paths or tests, run
`python tools/check_posix.py` — it re-runs the suite with `os.path` swapped
for `posixpath`, and additionally verifies over every recorded input that
only `dirname` changes between the two path flavours. Windows-only
assumptions are then caught locally instead of by CI on Linux and macOS.

The script also points each environment's pip at a mirror, so that manual
installs inside those venvs work on slow networks; the default lives in the
script itself and can be overridden or switched off with `-IndexUrl`.

The suite contains five layers:

1. `SnapshotTests` — per-field snapshots from `tests/fixtures/snapshot.json`
   plus sha256 digests that lock the parsing behaviour; both cover every field
   and are platform independent.
2. `NameInfoTests` — focused behaviour tests (padding limit, compound
   extensions, UV tiles, videos, writable attributes, ...).
3. `CommandLineTests` — the module import stays silent, `python -m name_info`
   output matches the snapshot data, user-supplied names are parsed, and `main()`
   is exercised in-process as well.
4. `DocumentationTests` — `docs/examples*.md` still matches the current output.
5. `PlatformPathTests` — Windows-only path forms (`D:shot.1001.exr`, UNC paths),
   asserted for whichever platform the suite happens to run on.

After an intentional behaviour change, refresh the snapshot file and paste the
new digests back into the test module:

```console
python tools/regenerate_snapshot.py
```

## Continuous integration

`.github/workflows/tests.yml` runs the suite on every push and pull request:

- `ubuntu-22.04`, `windows-latest` and `macos-latest`
- Python 3.7 through 3.14 (22 job combinations)

Two combinations are excluded on purpose: `macos-latest` is arm64 and
`setup-python` ships no arm64 builds for 3.7 / 3.8. The Linux leg is pinned to
`ubuntu-22.04` because 3.7 cannot be installed on 24.04 (no OpenSSL 1.1).

A second job builds the wheel, asserts that it ships `name_info/` and nothing
else, installs it, and calls `python -m name_info` from an unrelated directory.

The repository lives at <https://github.com/Wenfeng-Zhang/name-info>, where CI
runs on every push and pull request. For a fork or a fresh clone:

```console
git remote add origin git@github.com:<you>/name-info.git
git push -u origin main
```

## Project layout

```text
name_info/
├── name_info/__init__.py         # public re-exports and __version__
├── name_info/name_info.py        # NameInfo implementation
├── name_info/examples.py         # demo / snapshot inputs (not public API)
├── name_info/__main__.py         # python -m name_info entry point
├── tests/__init__.py             # keeps `unittest discover` working from the root
├── tests/test_name_info.py       # unittest suite
├── tests/fixtures/snapshot.json  # approved parsing snapshots
├── tools/regenerate_snapshot.py  # snapshot/digest regeneration
├── tools/build_example_docs.py   # generates docs/examples*.md from the code
├── tools/run_matrix.ps1          # local multi-interpreter test matrix
├── tools/check_posix.py          # runs the suite with os.path = posixpath
├── .github/workflows/tests.yml   # CI: 3 OS x Python 3.7-3.14, wheel smoke test
├── docs/parsing-rules.md         # detailed parsing rules
├── docs/examples.md              # every example next to its real output
└── pyproject.toml
```

## License

MIT — see [LICENSE](LICENSE).

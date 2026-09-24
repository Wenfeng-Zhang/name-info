#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Regenerate docs/examples.md and docs/examples.zh-CN.md from the package.

    python tools/build_example_docs.py

Every block in the generated pages is real ``NameInfo`` output, so the
documentation cannot drift from the implementation: change
``name_info/examples.py``, run this script, and the test suite will fail
until the pages match again.
"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))

from name_info import NameInfo
from name_info.examples import file_names


# Each group covers one aspect of the parser. Titles and notes come in
# (english, chinese) pairs. "inputs" must cover examples.file_names exactly once;
# the check at the bottom of this module enforces that.
GROUPS = (
    {
        "titles": ("Explicit frame placeholders", "显式帧占位符"),
        "notes": (
            "`%04d`, `####` and `$F4` outrank every numeric heuristic, and the "
            "text around the placeholder is kept (including a trailing `_beauty`).",
            "`%04d`、`####`、`$F4` 的优先级高于所有数字启发式规则，"
            "占位符前后的文本都会保留（包括末尾的 `_beauty`）。",
        ),
        "inputs": (
            "d:/render/testA_diffuse.%04d.exr",
            "d:/render/testA1001_diffuse.%04d.exr",
            "d:/render/testA_diffuse%04d.exr",
            "d:/render/testA_diffuse_%04d_beauty.exr",
            "d:/render/testA_diffuse_####_beauty.exr",
            "d:/render/testA_diffuse.####.exr",
            "d:/render/testA_diffuse####.exr",
            "d:/render/testA_diffuse.abc.$F4.exr",
            "d:/render/testA_diffuse.abc.layer.$F4.exr",
            "d:/render/testA_diffuse.$F4.exr",
            "d:/render/testA_$F4_diffuse.exr",
            "d:/render/testA_diffuse$F4.exr",
        ),
    },
    {
        "titles": ("UDIM textures", "UDIM 贴图"),
        "notes": (
            "`<UDIM>`, `<udim>` and `%(UDIM)d` all normalize to `<UDIM>` in the "
            "template, whichever side of the UDIM token the suffix sits on.",
            "`<UDIM>`、`<udim>`、`%(UDIM)d` 在 `template` 里统一归一为 `<UDIM>`，"
            "贴图后缀在 UDIM 前后都不影响识别。",
        ),
        "inputs": (
            "d:/render/testA<UDIM>_diffuse.exr",
            "d:/render/testA_diffuse10.<UDIM>.exr",
            "d:/render/testA_diffuse.%(UDIM)d.exr",
            "d:/render/testA_diffuse%(UDIM)d.exr",
            "d:/tex/testA10_mask_<UDIM>_8k.jpg",
            "d:/tex/testA_mask_<UDIM>_8k.jpg",
            "d:/tex/testA_leg_02_<UDIM>_Height.tif",
        ),
    },
    {
        "titles": ("UV tiles", "UV Tile"),
        "notes": (
            "Real UV tiles (`u1_v1`, `u10_v1`) and the `u<U>_v<V>` placeholder "
            "both stay case sensitive, and each coordinate keeps its own digit "
            "count in `wild_name` (`u10_v1` becomes `u??_v?`).",
            "实际的 UV Tile（`u1_v1`、`u10_v1`）与 `u<U>_v<V>` 占位符都保留大小写，"
            "`wild_name` 里每个坐标的位数独立（`u10_v1` 变成 `u??_v?`）。",
        ),
        "inputs": (
            "d:/tex/testA_diffuseu1_v1.exr",
            "d:/tex/testA_u1_v1_diffuse.exr",
            "d:/tex/testA_diffuse.u1_v1.1.exr",
            "d:/tex/testA_diffuse.u1_v1.exr",
            "d:/tex/testA_u10_v1.exr",
            "d:/tex/testA_diffuse.u<U>_v<V>.exr",
            "d:/tex/testA_diffuseu<U>_v<V>.exr",
            "d:/tex/testA_u<U>_v<V>diffuse.exr",
            "d:/tex/testA_U<U>_V<V>.exr",
        ),
    },
    {
        "titles": ("Four-digit frame numbers", "四位帧号"),
        "notes": (
            "The VFX default: a standalone four-digit run at the end of the stem. "
            "Watch how the delimiter next to the frame survives "
            "(`leg_02_1021_Height` -> `leg_02_Height`).",
            "VFX 最常见的格式：主体末尾独立的四位数字。"
            "注意紧邻帧号的分隔符会被保留（`leg_02_1021_Height` → `leg_02_Height`）。",
        ),
        "inputs": (
            "d:/render/testA_diffuse_v0028.1001.exr",
            "d:/render/testA_diffuse1001.exr",
            "d:/render/testA.beauty1001.exr",
            "d:/render/show_20260924_asset.exr",
            "d:/render/shot.1001.1001.ext",
            "d:/tex/testA_mask_1001_8k_<UDIM>.jpg",
            "d:/tex/testA_mask_1001_8k.jpg",
            "d:/tex/testA.mask_1001_8k.jpg",
            "d:/tex/testA_leg_02_1021_Height.tif",
            "d:/tex/testA_leg_02.1021_Height.tif",
            "d:/tex/testA_leg_xy.02_1021_Height.tif",
            "d:/tex/testA_leg_xy.1021_Height.tif",
            "d:/tex/testA_leg_xy._1021_Height.tif",
            "d:/tex/testA_leg_02_<UDIM>(1).tif",
            "d:/tex/testA_leg_02_1001(1).tif",
            "d:/tex/testA_1234_mask_4K_1001.jpg",
        ),
    },
    {
        "titles": ("Versions and static names", "版本号与静态名"),
        "notes": (
            "A trailing `v001` is a version, not a frame, so no sequence pattern "
            "is reported and `template` returns the path unchanged. The last entry "
            "has no extension at all, which is why its output is empty.",
            "结尾的 `v001` 是版本号而不是帧号，因此不会识别出序列模式，"
            "`template` 原样返回路径。最后一条完全没有扩展名，所以输出为空。",
        ),
        "inputs": (
            "d:/render/testA_diffusev001.exr",
            "d:/render/shot_v002_final.exr",
            "d:/render/shot_v1001_diff.exr",
            "d:/render/testA_0110_key_master_v009.exr",
            "d:/render/testA",
        ),
    },
    {
        "titles": ("Textures, caches and compound extensions", "贴图、缓存与复合扩展名"),
        "notes": (
            "Compound suffixes (`.bgeo.sc`, `.ass.gz`, `.exr.gz`, `.exr.bak`) stay "
            "intact, and a `.tx` cache keeps `tx` as the extension after stripping "
            "the inner image extension.",
            "复合后缀（`.bgeo.sc`、`.ass.gz`、`.exr.gz`、`.exr.bak`）整体保留；"
            "`.tx` 缓存会把内层图像扩展名剥掉，只留 `tx` 作为扩展名。",
        ),
        "inputs": (
            "d:/render/testA.1001.exr.gz",
            "d:/render/testA.1001.exr.bak",
            "d:/tex/testA_154_022_leaf_diffuse_02.jpg",
            "d:/cache/testA_154_022_leaf_.diffuse_02.bgeo.sc",
            "d:/cache/testA_154_022_leaf_.diffuse_02.ass.gz",
            "d:/tex/testA_body_coat_8k_1001_Raw_scene-linear Rec 709_sRGB.tif.tx",
            "d:/tex/testA_body_coat_8k_<UDIM>_Raw_scene-linear Rec 709_sRGB.tif.tx",
            "d:/tex/testA_cloth_col_4k.<udim>_sRGB_scene-linear Rec 709_sRGB.tif.tx",
            "d:/tex/testA_cloth_col_4k.1001_sRGB_scene-linear Rec 709_sRGB.tif.tx",
        ),
    },
    {
        "titles": ("View tokens and videos", "眼位标记与视频"),
        "notes": (
            "`%V` is recorded as `other_pattern` next to the frame placeholder, "
            "and video files skip pattern detection entirely.",
            "`%V` 会作为 `other_pattern` 与帧占位符并存记录；"
            "视频文件则完全不做模式检测。",
        ),
        "inputs": (
            "d:/render/testA.%04d.%V.exr",
            "d:/render/testA2_Bokeh_DOF_04.mp4",
        ),
    },
)


HEADERS = (
    "# Parsing examples\n"
    "\n"
    "Every block below is real `python -m name_info` output: the input line, then\n"
    "the resulting `NameInfo` attributes. The inputs are exactly the ones in\n"
    "`name_info/examples.py`; run `python -m name_info` to see the same output\n"
    "locally, or pass your own paths. Rule details live in\n"
    "[parsing-rules.md](parsing-rules.md).\n"
    "\n"
    "The same page is generated for the examples in Chinese:\n"
    "[examples.zh-CN.md](examples.zh-CN.md).\n",
    "# 解析示例\n"
    "\n"
    "下面每一块都是 `python -m name_info` 的真实输出：第一行是输入，随后是\n"
    "`NameInfo` 解析出的各个属性。输入与 `name_info/examples.py` 完全一致，\n"
    "本地跑 `python -m name_info` 就能看到同样的结果，也可以传入自己的路径。\n"
    "规则细节见 [parsing-rules.zh-CN.md](parsing-rules.zh-CN.md)。\n"
    "\n"
    "同一份内容另有英文版：[examples.md](examples.md)。\n",
)


def render_group(index, group, language):
    """Render one group as a heading, a note and a block of real output."""
    lines = [
        "## {0}. {1}".format(index, group["titles"][language]),
        "",
        group["notes"][language],
        "",
        "```text",
    ]
    blocks = []
    for filename in group["inputs"]:
        blocks.append("{0}\n{1}".format(filename, NameInfo(filename)))
    lines.append("\n\n".join(blocks))
    lines.extend(["```", ""])
    return "\n".join(lines)


def build_docs(language):
    """Return the whole page (0 = english, 1 = chinese) as a string."""
    parts = [HEADERS[language], ""]
    for index, group in enumerate(GROUPS, 1):
        parts.append(render_group(index, group, language))
    return "\n".join(parts)


def documented_inputs():
    """Every input referenced by GROUPS, in page order."""
    return [filename for group in GROUPS for filename in group["inputs"]]


def assert_full_coverage():
    """The groups must cover examples.file_names exactly once, without gaps."""
    documented = documented_inputs()
    duplicates = sorted({name for name in documented if documented.count(name) > 1})
    if duplicates:
        raise AssertionError("duplicated in GROUPS: {0}".format(duplicates))
    missing = sorted(set(file_names) - set(documented))
    if missing:
        raise AssertionError("missing from GROUPS: {0}".format(missing))
    unknown = sorted(set(documented) - set(file_names))
    if unknown:
        raise AssertionError("not in examples.file_names: {0}".format(unknown))


assert_full_coverage()


def main():
    for language, name in ((0, "examples.md"), (1, "examples.zh-CN.md")):
        path = ROOT / "docs" / name
        with open(str(path), "w", encoding="utf-8", newline="\n") as stream:
            stream.write(build_docs(language))
        print("wrote {0}".format(path))


if __name__ == "__main__":
    main()

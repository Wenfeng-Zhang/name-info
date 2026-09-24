"""解析结果的快照测试与公开接口测试。

在项目根目录运行：

    python -m unittest discover

缺失依赖为零：测试只用标准库的 unittest，不需要额外安装。
"""

import contextlib
import hashlib
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "snapshot.json"

# 包就在项目根下：先把它加入 sys.path，未安装也能 import
# （discover / pytest / 直接运行都适用）。
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import name_info
from name_info import NameInfo
from name_info.__main__ import build_parser, main
from name_info.examples import file_names


# 逐字段快照的字段顺序，同时也是 fixture 中 expected 的字段顺序。
# 边界用例里刻意不放依赖 os.path 的输入（"D:shot.1001.exr"、UNC 路径见
# 文件末尾的 PlatformPathTests），因此快照与指纹在所有平台都完全一致。
FIELDS = (
    "filename", "basename", "dirname", "name", "pattern", "ext",
    "absname", "padding", "wild_name", "other_pattern", "template",
)

EXAMPLES_COUNT = 60
EDGES_COUNT = 120
MATRIX_COUNT = 2016

APPROVED_DIGESTS = {
    "examples": "87159d4f973dc594b3b2ac1c78d4bfe2d8edf2868b5be298fa096a6d6b29b086",
    "edges": "1d74772dcc760933490d12ae4194c3e1bcf681eca269aeba3816e6cdbe80e0e2",
    "matrix": "95d141113362328960a1a067ddceb20dc168471fa093a5acbaca1e0e70f04f40",
}


def snapshot(filename):
    """把一条输入解析成逐字段快照。"""
    value = NameInfo(filename)
    result = {field: getattr(value, field) for field in FIELDS}
    result["repr"] = repr(value)
    result["str"] = str(value)
    return result


def cases_digest(filenames):
    """计算 (条数, sha256)，逐字段锁定全部解析结果，且与平台无关。"""
    hasher = hashlib.sha256()
    count = 0
    for filename in filenames:
        data = snapshot(filename)
        hasher.update(
            json.dumps(data, sort_keys=True, ensure_ascii=True).encode("ascii")
        )
        hasher.update(b"\n")
        count += 1
    return count, hasher.hexdigest()


def edge_cases():
    """覆盖空名、无扩展名、路径形式、占位符、双后缀等边界输入。"""
    paths = [
        "", " ", "README", ".hidden", "file.", ".", "..", "D:/folder/",
        "shot.1001.exr", "shot..1001.exr", "plain.exr", "plain.weird",
        "shot.1001.1001", "1001.exr", "asset_10001_8k.exr",
        "asset_123456_8k.exr", "asset_20001_8k.exr",
        "a_1001_b_1002_8k.exr", "a_1001_b_1001_8k.exr",
        "a_02_b_03.exr", "a_02_b_02_suffix.exr", "tex_1001(1).tif",
        "tex_1001_Height.tif", "tex_1001_8k.tif",
        "shot_v001.exr", "shot_V1001.exr", "shot_v1001_diff.exr",
        "shot_1001_v002.exr", "tex_u1_v1.exr", "tex_u10_v1.exr",
        "tex_u1_v10.exr", "tex_u10_v10_diff.exr", "tex_U12_V34_diff.exr",
        "tex_u1_v1.1.exr", "tex_u1_v1_u1_v1_diff.exr",
        "a_u<U>_v<V>_b_u<U>_v<V>.exr", "a_U<U>_V<V>_diff.exr",
        "a_%04d_b_%04d.exr", "a_%04d_b_####.exr",
        "a_<udim>_b_<UDIM>.exr", "a_1001.exr.tx", "a_1001.foo.tx",
        "a_1001.bgeo.sc.tx", "a_1001.TIF.TX", "a_1001.tx",
        "/shot.1001.exr",
        r"  D:\mixed/path\shot.1001.exr  ",
        "D://folder///shot.1001.exr",
        "D:/folder.with.1001/plain.exr",
        "\u8d44\u4ea7_\u8d34\u56fe.1001.exr", "tex.\uff11\uff10\uff10\uff11.exr",
        # 占位符也会命中普通单词；这些输入把“已知限制”本身锁进快照。
        "cache_$Frame.exr", "x$Foo.exr", "pct_100%discount.exr",
        "note_10#_v1.exr", "plate_1001_2001.exr",
    ]
    for pattern in (
        "%d", "%0d", "%4d", "%04d", "%08d", "%04D", "#", "####",
        "$F", "$F0", "$F4", "$f4", "<UDIM>", "<udim>",
        "%(UDIM)d", "%(udim)d", "u<U>_v<V>", "U<U>_V<V>",
    ):
        paths.extend(("tex.{}.exr".format(pattern),
                      "tex_{}_diff.exr".format(pattern)))
    for ext in (
        "bgeo.sc", "bgeo.gz", "ass.gz", "vdb.sc", "vdb.gz", "tar.gz",
        "mp4", "mov", "avi", "mkv", "webm", "exr", "dpx", "tif",
    ):
        paths.extend(("shot.1001." + ext, "shot.1001." + ext.upper()))
    return paths


def matrix_cases():
    """组合前缀、模式、后缀与扩展名，覆盖优先级与重复模式。"""
    for prefix, pattern, suffix, ext in itertools.product(
        ("asset_", "asset_1001_", "asset_v002_", "asset_u1_v1_"),
        ("02", "1001", "10001", "20001", "v001", "u1_v1", "u10_v1",
         "%04d", "$F4", "<UDIM>", "<udim>", "u<U>_v<V>"),
        ("", "_diff", "_8k", "_1001", "(1)", ".1", "_v001"),
        (".exr", ".tif.tx", ".bgeo.sc", ".MP4", ".unknown", ""),
    ):
        yield prefix + pattern + suffix + ext


class SnapshotTests(unittest.TestCase):
    """逐字段快照：fixture 里的预期必须与当前实现完全一致。"""

    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def assert_snapshot(self, case):
        self.assertEqual(snapshot(case["input"]), case["expected"])

    def test_examples_snapshot(self):
        cases = self.baseline["examples"]
        self.assertEqual(len(cases), EXAMPLES_COUNT)
        self.assertEqual([case["input"] for case in cases], file_names)
        for case in cases:
            with self.subTest(filename=case["input"]):
                self.assert_snapshot(case)

    def test_edges_snapshot(self):
        cases = self.baseline["edges"]
        self.assertEqual(len(cases), EDGES_COUNT)
        self.assertEqual([case["input"] for case in cases], edge_cases())
        for case in cases:
            with self.subTest(filename=case["input"]):
                self.assert_snapshot(case)

    def test_examples_digest(self):
        count, digest = cases_digest(file_names)
        self.assertEqual(count, EXAMPLES_COUNT)
        self.assertEqual(digest, APPROVED_DIGESTS["examples"])

    def test_edges_digest(self):
        count, digest = cases_digest(edge_cases())
        self.assertEqual(count, EDGES_COUNT)
        self.assertEqual(digest, APPROVED_DIGESTS["edges"])

    def test_matrix_digest(self):
        count, digest = cases_digest(matrix_cases())
        self.assertEqual(count, MATRIX_COUNT)
        self.assertEqual(digest, APPROVED_DIGESTS["matrix"])


class PlatformPathTests(unittest.TestCase):
    """Windows 专属路径形式：os.path 本身就不同，因此单独按平台断言。

    这些输入不进快照也不进指纹，理由见 FIELDS 处的注释。
    """

    def test_drive_relative_path(self):
        value = NameInfo("D:shot.1001.exr")
        if os.name == "nt":
            self.assertEqual(value.dirname, "D:")
            self.assertEqual(value.basename, "shot.1001.exr")
            self.assertEqual(value.name, "shot.")
            self.assertEqual(value.absname, "shot")
            self.assertEqual(value.template, "D:/shot.%04d.exr")
        else:
            # posixpath 不认盘符，"D:" 会留在文件名里。
            self.assertEqual(value.dirname, "")
            self.assertEqual(value.basename, "D:shot.1001.exr")
            self.assertEqual(value.name, "D:shot.")
            self.assertEqual(value.absname, "D:shot")
            self.assertEqual(value.template, "D:shot.%04d.exr")
        self.assertEqual(value.pattern, "1001")
        self.assertEqual(value.padding, 4)

    def test_unc_path(self):
        value = NameInfo("//server/share/shot.1001.exr")
        if os.name == "nt":
            # ntpath 会保留结尾的斜杠。
            self.assertEqual(value.dirname, "//server/share/")
        else:
            self.assertEqual(value.dirname, "//server/share")
        self.assertEqual(value.basename, "shot.1001.exr")
        self.assertEqual(value.name, "shot.")
        self.assertEqual(value.template, "//server/share/shot.%04d.exr")


class NameInfoTests(unittest.TestCase):
    def test_one_sequence_many_spellings(self):
        """%04d、####、具体帧号与 $F4 指向同一个序列（对应 README 的“为什么”一节）。"""
        spellings = ("d:/a.%04d.exr", "d:/a.####.exr", "d:/a.1001.exr", "d:/a.$F4.exr")
        infos = [NameInfo(path) for path in spellings]
        self.assertEqual({(i.dirname, i.absname, i.ext) for i in infos},
                         {("d:/", "a", "exr")})
        for info in infos:
            self.assertEqual(info.absname, "a")
            self.assertEqual(info.padding, 4)
            self.assertEqual(info.wild_name, "a.????")
        # 写法本身（pattern）故意不同；template 保留各自的风格，不做归一。
        self.assertEqual([info.pattern for info in infos],
                         ["%04d", "####", "1001", "$F4"])
        self.assertEqual(NameInfo("d:/a.1001.exr").template, "d:/a.%04d.exr")
        self.assertEqual(NameInfo("d:/a.####.exr").template, "d:/a.####.exr")

    def test_path_normalization(self):
        value = NameInfo(r"  D:\mixed/path\shot.1001.exr  ")
        self.assertEqual(value.filename, "D:/mixed/path/shot.1001.exr")
        self.assertEqual(value.dirname, "D:/mixed/path")
        self.assertEqual(value.basename, "shot.1001.exr")

    def test_missing_extension_defaults(self):
        for filename in ("", "README", ".hidden", "file."):
            with self.subTest(filename=filename):
                value = NameInfo(filename)
                for field in ("name", "pattern", "absname", "wild_name"):
                    self.assertIsNone(getattr(value, field))
                self.assertEqual(value.ext, "")
                self.assertEqual(value.padding, 0)
                self.assertEqual(value.template, filename)
                self.assertEqual(str(value), "")

    def test_numeric_output(self):
        value = NameInfo("D:/render/shot.1001.exr")
        self.assertEqual(
            (value.name, value.pattern, value.ext, value.absname,
             value.padding, value.wild_name, value.template),
            ("shot.", "1001", "exr", "shot", 4, "shot.????",
             "D:/render/shot.%04d.exr"),
        )

    def test_legacy_names_are_gone(self):
        """旧命名已全部移除，避免两套名字并存。"""
        for legacy in ("NameFormat", "VALID_EXTS"):
            self.assertFalse(hasattr(name_info, legacy))
        value = NameInfo("shot.1001.exr")
        for legacy in ("root", "pattern_num", "extra_pattern"):
            self.assertFalse(hasattr(value, legacy))
            with self.assertRaises(AttributeError):
                setattr(value, legacy, "changed")

    def test_examples_are_not_part_of_the_api(self):
        """示例数据只服务演示与测试，不从包顶层导出。"""
        self.assertFalse(hasattr(name_info, "file_names"))
        self.assertEqual(len(file_names), EXAMPLES_COUNT)
        self.assertEqual(len(set(file_names)), EXAMPLES_COUNT)

    def test_public_fields_are_writable(self):
        value = NameInfo("shot.1001.exr")
        value.absname = "changed"
        value.wild_name = "changed.????"
        self.assertEqual((value.absname, value.wild_name),
                         ("changed", "changed.????"))

    def test_template_replaces_stem_not_extension(self):
        value = NameInfo("shot.1001.1001.ext")
        self.assertEqual(value.pattern, "1001")
        self.assertEqual(value.template, "shot.1001.%04d.ext")
        self.assertEqual(value.wild_name, "shot.1001.????")
        self.assertEqual(NameInfo("shot.1001.1001").template,
                         "shot.%04d.1001")

    def test_padding_limit(self):
        for pattern in ("%257d", "$F257", "#" * 257, "1" * 257):
            with self.subTest(pattern=pattern[:20]):
                with self.assertRaises(ValueError):
                    NameInfo("shot." + pattern + ".exr")
        self.assertEqual(NameInfo("shot.%256d.exr").padding, 256)

    def test_version_inside_stem_is_not_a_frame(self):
        for filename in ("shot_v002_final.exr", "shot_v1001_diff.exr"):
            with self.subTest(filename=filename):
                value = NameInfo(filename)
                self.assertEqual(value.pattern, "")
                self.assertEqual(value.name, filename[:-4])
                self.assertIsNone(value.other_pattern)
        self.assertEqual(NameInfo("shot_v0028.1001.exr").pattern, "1001")

    def test_eight_digit_numbers_are_not_auto_classified_as_dates(self):
        self.assertEqual(NameInfo("show_20260924_asset.exr").pattern,
                         "20260924")
        self.assertEqual(NameInfo("shot.20260924.exr").pattern, "20260924")

    def test_other_pattern_is_optional_and_does_not_change_primary(self):
        cases = (
            ("shot.1001.exr", "1001", None),
            ("tex_u10_v1.exr", "u10_v1", None),
            ("tex_u1_v1.1001.exr", "1001", "u1_v1"),
            ("tex_u<U>_v<V>.%04d.exr", "u<U>_v<V>", "%04d"),
            ("shot.%04d.%V.exr", "%04d", "%V"),
            ("shot.%04d.%v.exr", "%04d", "%v"),
            ("tex_u1_v1.1.exr", "1", "u1_v1"),
            ("README", None, None),
        )
        for filename, pattern, other in cases:
            with self.subTest(filename=filename):
                value = NameInfo(filename)
                self.assertEqual(value.pattern, pattern)
                self.assertEqual(value.other_pattern, other)

    def test_keep_suffix_for_explicit_and_numeric_patterns(self):
        cases = (
            ("tex_%04d_diff.exr", "tex_diff"),
            ("tex_1001_diff.exr", "tex_diff"),
            ("tex_1001_8k.exr", "tex_8k"),
            ("tex_u1_v1_diff.exr", "tex_diff"),
        )
        for filename, name in cases:
            with self.subTest(filename=filename):
                self.assertEqual(NameInfo(filename).name, name)

    def test_preserve_delimiter_adjacent_to_pattern(self):
        cases = (
            ("leg_02_1021_Height.tif", "leg_02_Height"),
            ("leg_02.1021_Height.tif", "leg_02.Height"),
            ("leg_xy.1021_Height.tif", "leg_xy.Height"),
            ("leg_xy._1021_Height.tif", "leg_xy._Height"),
            ("cloth_4k.<udim>_sRGB.tif.tx", "cloth_4k.sRGB"),
            ("cloth_4k.1001_sRGB.tif.tx", "cloth_4k.sRGB"),
            ("asset-1001_diff.exr", "asset-diff"),
            ("asset1001-diff.exr", "asset-diff"),
            ("asset1001diff.exr", "asset_diff"),
        )
        for filename, name in cases:
            with self.subTest(filename=filename):
                value = NameInfo(filename)
                self.assertEqual(value.name, name)
                self.assertEqual(value.absname, name.rstrip("."))

    def test_examples_with_patterns_before_suffixes(self):
        cases = (
            ("d:/show/seq010/shot020/render/chrHero<UDIM>_diffuse.exr",
             "chrHero_diffuse", "<UDIM>", "chrHero????_diffuse"),
            ("d:/show/seq010/shot020/render/chrHero_$F4_diffuse.exr",
             "chrHero_diffuse", "$F4", "chrHero_????_diffuse"),
            ("d:/show/assets/textures/20240329/SHOW_chr_Hero_mask_<UDIM>_8k.jpg",
             "SHOW_chr_Hero_mask_8k", "<UDIM>", "SHOW_chr_Hero_mask_????_8k"),
            ("d:/show/assets/textures/20240329/SHOW_chr_Hero10_mask_<UDIM>_8k.jpg",
             "SHOW_chr_Hero10_mask_8k", "<UDIM>", "SHOW_chr_Hero10_mask_????_8k"),
            ("d:/show/assets/textures/20240329/leg_02_<UDIM>(1).tif",
             "leg_02_(1)", "<UDIM>", "leg_02_????(1)"),
            ("d:/show/assets/textures/leg_02_1001(1).tif",
             "leg_02_(1)", "1001", "leg_02_????(1)"),
            ("d:/assetHero_chr_Hero_Body_Coat_8k_<UDIM>_Raw_scene-linear Rec 709_sRGB.tif.tx",
             "assetHero_chr_Hero_Body_Coat_8k_Raw_scene-linear Rec 709_sRGB",
             "<UDIM>",
             "assetHero_chr_Hero_Body_Coat_8k_????_Raw_scene-linear Rec 709_sRGB"),
        )
        for filename, name, pattern, wild_name in cases:
            with self.subTest(filename=filename):
                value = NameInfo(filename)
                self.assertEqual(value.name, name)
                self.assertEqual(value.absname, name.rstrip("."))
                self.assertEqual(value.pattern, pattern)
                self.assertEqual(value.wild_name, wild_name)

    def test_preserve_long_thousands_prefix(self):
        value = NameInfo("asset_10001_8k.exr")
        self.assertEqual(value.pattern, "10001")
        self.assertEqual(value.padding, 5)
        self.assertEqual(value.wild_name, "asset_?????_8k")

    def test_multi_digit_uv_with_version_exclusion(self):
        self.assertEqual(NameInfo("tex_u10_v1.exr").pattern, "u10_v1")
        self.assertEqual(NameInfo("tex_u10_v1.exr").wild_name, "tex_u??_v?")
        self.assertEqual(NameInfo("tex_u1_v1.exr").pattern, "u1_v1")

    def test_normalize_udim_and_uv_placeholder_case(self):
        self.assertEqual(NameInfo("tex.<udim>.exr").template, "tex.<UDIM>.exr")
        self.assertEqual(NameInfo("tex.%(UDIM)d.exr").template, "tex.<UDIM>.exr")
        self.assertEqual(
            NameInfo("tex.U<U>_V<V>.exr").wild_name, "tex.U?_V?"
        )

    def test_repeated_pattern_uses_last_occurrence(self):
        value = NameInfo("a_%04d_b_%04d.exr")
        self.assertEqual(value.name, "a_%04d_b_")
        self.assertEqual(value.wild_name, "a_%04d_b_????")

    def test_tx_keeps_original_extension_in_template(self):
        value = NameInfo("shot.1001.TIF.TX")
        self.assertEqual(value.ext, "tx")
        self.assertEqual(value.wild_name, "shot.????")
        self.assertEqual(value.template, "shot.%04d.TIF.TX")

    def test_all_supported_inner_tx_extensions(self):
        for ext in sorted(NameInfo.KNOWN_EXTS):
            for spelling in (ext, ext.upper()):
                with self.subTest(ext=spelling):
                    value = NameInfo("shot.1001" + spelling + ".tx")
                    self.assertEqual(value.ext, "tx")
                    self.assertEqual(value.name, "shot.")
                    self.assertEqual(value.pattern, "1001")
                    self.assertEqual(value.wild_name, "shot.????")
                    self.assertEqual(value.template, "shot.%04d" + spelling + ".tx")

    def test_uv_output_preserves_case_and_repeated_digits(self):
        for pattern, wildcard in (
            ("u11_v11", "u??_v??"), ("U11_V11", "U??_V??"),
            ("u1_V11", "u?_V??"), ("u12_v2", "u??_v?"),
        ):
            with self.subTest(pattern=pattern):
                value = NameInfo("tex_" + pattern + "_diff.exr")
                self.assertEqual(value.pattern, pattern)
                self.assertEqual(value.name, "tex_diff")
                self.assertEqual(value.padding, 0)
                self.assertEqual(value.wild_name, "tex_" + wildcard + "_diff")
                self.assertEqual(value.template, value.filename)

    def test_video_bypasses_pattern_detection(self):
        for ext in ("mp4", "MOV", "avi", "MKV", "webm"):
            with self.subTest(ext=ext):
                value = NameInfo("shot.%04d." + ext)
                self.assertEqual(value.pattern, "")
                self.assertEqual(value.name, "shot.%04d")
                self.assertEqual(value.template, value.filename)

    def test_repr_and_str(self):
        value = NameInfo("shot.1001.exr")
        expected = (
            "name='shot.', pattern='1001', ext='exr', absname='shot', "
            "padding=4, wild_name='shot.????'"
        )
        self.assertEqual(repr(value), expected)
        self.assertEqual(str(value), expected)

    def test_slots_reject_unknown_attributes(self):
        value = NameInfo("shot.1001.exr")
        with self.assertRaises(AttributeError):
            value.unrecognized = True

    def test_template_tracks_public_attribute_changes(self):
        value = NameInfo("shot.1001.exr")
        value.dirname = "other"
        self.assertEqual(value.template, "other/shot.%04d.exr")
        value.padding = 6
        self.assertEqual(value.template, "other/shot.%06d.exr")
        value.basename = "other.1001.exr"
        self.assertEqual(value.template, "other/other.%06d.exr")
        value.pattern = "1002"
        self.assertEqual(value.template, "other/other.1001.exr")

    def test_requested_behavior(self):
        height = NameInfo("leg_02_<UDIM>_Height.tif")
        self.assertEqual(height.name, "leg_02_Height")
        self.assertEqual(height.wild_name, "leg_02_????_Height")
        self.assertEqual(
            NameInfo("C:/shot.1001.exr").template, "C:/shot.%04d.exr"
        )
        frame = NameInfo("shot.123.v002.exr")
        self.assertEqual(frame.pattern, "123")
        self.assertEqual(frame.template, "shot.%03d.v002.exr")
        uv = NameInfo("tex_u1_v1_v002.exr")
        self.assertEqual(uv.pattern, "u1_v1")
        self.assertEqual(uv.wild_name, "tex_u?_v?_v002")
        self.assertEqual(
            NameInfo("tex.<udim>.exr").template, "tex.<UDIM>.exr"
        )
        self.assertEqual(NameInfo("shot.1001.EXR").ext, "exr")

    def test_keep_confirmed_version_and_numeric_behavior(self):
        single = NameInfo("D:/a/mbh_0110_key_master_v009.exr")
        self.assertEqual(single.pattern, "")
        self.assertEqual(single.template, single.filename)
        numbered = NameInfo("d:/aaa/miniPanda_diff_v0028.1001.exr")
        self.assertEqual(numbered.pattern, "1001")
        self.assertEqual(
            numbered.template, "d:/aaa/miniPanda_diff_v0028.%04d.exr"
        )
        self.assertEqual(NameInfo("a.1001.exr").pattern, "1001")

    def test_date_does_not_override_explicit_placeholder(self):
        value = NameInfo("show_20260924_asset.%04d.exr")
        self.assertEqual(value.pattern, "%04d")
        self.assertEqual(value.name, "show_20260924_asset.")
        self.assertEqual(value.wild_name, "show_20260924_asset.????")

    def test_additional_production_examples(self):
        cases = (
            ("d:/render/testA.%04d.%V.exr",
             "testA.%V", "testA.%V", "%04d", "exr", 4,
             "testA.????.%V", "d:/render/testA.%04d.%V.exr"),
            ("d:/render/testA.1001.exr.gz",
             "testA.", "testA", "1001", "exr.gz", 4,
             "testA.????", "d:/render/testA.%04d.exr.gz"),
            ("d:/render/testA.1001.exr.bak",
             "testA.", "testA", "1001", "exr.bak", 4,
             "testA.????", "d:/render/testA.%04d.exr.bak"),
        )
        for filename, name, absname, pattern, ext, width, wild_name, template in cases:
            with self.subTest(filename=filename):
                value = NameInfo(filename)
                self.assertEqual(
                    (value.name, value.absname, value.pattern, value.ext,
                     value.padding, value.wild_name, value.template),
                    (name, absname, pattern, ext, width, wild_name, template),
                )

    def test_double_extension_is_specific_and_case_insensitive(self):
        for filename, ext in (
            ("testA.1001.EXR.GZ", "exr.gz"),
            ("testA.1001.EXR.BAK", "exr.bak"),
            ("testA.1001.foo.gz", "gz"),
            ("testA.1001.foo.bak", "bak"),
        ):
            with self.subTest(filename=filename):
                value = NameInfo(filename)
                self.assertEqual(value.ext, ext)
                if ext.startswith("exr."):
                    self.assertEqual(value.name, "testA.")
                    self.assertEqual(value.wild_name, "testA.????")
                else:
                    self.assertEqual(value.name, "testA.foo")

    def test_important_inputs_stay_in_examples(self):
        cases = (
            "d:/render/shot.1001.1001.ext",
            "d:/render/shot_v002_final.exr",
            "d:/render/shot_v1001_diff.exr",
            "d:/render/show_20260924_asset.exr",
        )
        for filename in cases:
            self.assertIn(filename, file_names)

    def test_uv_placeholder_replaces_all_occurrences(self):
        value = NameInfo("a_u<U>_v<V>_b_u<U>_v<V>.exr")
        self.assertEqual(value.pattern, "u<U>_v<V>")
        self.assertEqual(value.wild_name, "a_u?_v?_b_u?_v?")

    def test_version_attribute(self):
        self.assertRegex(name_info.__version__, r"^\d+\.\d+\.\d+$")


class CommandLineTests(unittest.TestCase):
    """模块作为脚本运行时的输出必须与快照一致。"""

    @staticmethod
    def subprocess_env():
        env = dict(os.environ)
        parts = [str(ROOT)]
        if env.get("PYTHONPATH"):
            parts.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(parts)
        return env

    def run_python(self, arguments):
        return subprocess.run(
            [sys.executable] + arguments, cwd=str(ROOT),
            env=self.subprocess_env(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True, check=True,
        )

    def test_import_is_silent(self):
        process = self.run_python(["-c", "import name_info"])
        self.assertEqual(process.stdout, "")
        self.assertEqual(process.stderr, "")

    def test_module_runs_as_script(self):
        process = self.run_python(["-m", "name_info"])
        self.assertEqual(process.stderr, "")
        self.assertEqual(
            process.stdout,
            "".join("{}\n{}\n\t\n".format(filename, NameInfo(filename))
                    for filename in file_names),
        )

    def test_user_supplied_filenames_are_parsed(self):
        """用户可以直接把自己的路径交给命令行来打印解析结果。"""
        inputs = ("shot.1001.exr", "d:/render/plate.%04d.exr", "tex_u10_v1.exr")
        process = self.run_python(["-m", "name_info"] + list(inputs))
        self.assertEqual(process.stderr, "")
        self.assertEqual(
            process.stdout,
            "".join("{}\n{}\n\t\n".format(filename, NameInfo(filename))
                    for filename in inputs),
        )

    def test_help_lists_usage(self):
        process = self.run_python(["-m", "name_info", "--help"])
        self.assertIn("usage", process.stdout.lower())
        self.assertIn("filenames", process.stdout)

    def test_entry_point_parses_given_names_in_process(self):
        """直接调用 main()，让 __main__ 模块本身也被覆盖（subprocess 不计入覆盖率）。"""
        self.assertEqual(build_parser().prog, "python -m name_info")
        inputs = ("shot.1001.exr", "tex_u10_v1.exr")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main(list(inputs))
        self.assertEqual(
            buffer.getvalue(),
            "".join("{}\n{}\n\t\n".format(filename, NameInfo(filename))
                    for filename in inputs),
        )

    def test_entry_point_without_arguments_uses_the_examples(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main([])
        self.assertEqual(
            buffer.getvalue(),
            "".join("{}\n{}\n\t\n".format(filename, NameInfo(filename))
                    for filename in file_names),
        )


class DocumentationTests(unittest.TestCase):
    """The generated example pages must stay in sync with the implementation."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "build_example_docs", str(ROOT / "tools" / "build_example_docs.py")
        )
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    def test_example_pages_are_current(self):
        for language, name in ((0, "examples.md"), (1, "examples.zh-CN.md")):
            with self.subTest(page=name):
                path = ROOT / "docs" / name
                self.assertTrue(path.is_file(), "{} is missing".format(name))
                self.assertEqual(
                    path.read_text(encoding="utf-8"),
                    self.builder.build_docs(language),
                    "{} is stale; run python tools/build_example_docs.py".format(name),
                )


if __name__ == "__main__":
    unittest.main()

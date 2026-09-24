#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""重新生成 tests/fixtures/snapshot.json，并打印需要回填到测试里的指纹。

只有在意变更了 ``NameInfo`` 的解析行为、并确认新行为正确之后，才运行本脚本：

    python tools/regenerate_snapshot.py

脚本会覆盖快照文件，并把三组用例的条数与 sha256 打印出来，需要手动粘回
``tests/test_name_info.py`` 里的 ``EXAMPLES_COUNT`` / ``EDGES_COUNT`` /
``MATRIX_COUNT`` 与 ``APPROVED_DIGESTS``。
"""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import test_name_info as tests
from name_info.examples import file_names


DESCRIPTION = (
    "Approved parsing snapshots for NameInfo. Every entry is produced by "
    "NameInfo itself; regenerate with tools/regenerate_snapshot.py only after "
    "an intentional behaviour change. basename/dirname/template are captured "
    "on Windows, because they come from os.path."
)


def main():
    fixture = {
        "description": DESCRIPTION,
        "examples": [
            {"input": filename, "expected": tests.snapshot(filename)}
            for filename in file_names
        ],
        "edges": [
            {"input": filename, "expected": tests.snapshot(filename)}
            for filename in tests.edge_cases()
        ],
    }
    tests.FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    tests.FIXTURE.write_text(
        json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("wrote {}".format(tests.FIXTURE))

    groups = (
        ("examples", file_names),
        ("edges", tests.edge_cases()),
        ("matrix", tests.matrix_cases()),
    )
    for key, filenames in groups:
        count, digest = tests.cases_digest(filenames)
        print('{}: count={} sha256="{}"'.format(key, count, digest))


if __name__ == "__main__":
    main()

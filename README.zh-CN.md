[English](README.md) | **中文**

[![tests](https://github.com/Wenfeng-Zhang/name-info/actions/workflows/tests.yml/badge.svg)](https://github.com/Wenfeng-Zhang/name-info/actions/workflows/tests.yml)
[![python](https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://github.com/Wenfeng-Zhang/name-info/blob/main/pyproject.toml)
[![platforms](https://img.shields.io/badge/platforms-linux%20%7C%20windows%20%7C%20macos-lightgrey)](https://github.com/Wenfeng-Zhang/name-info/actions/workflows/tests.yml)
[![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](https://github.com/Wenfeng-Zhang/name-info/blob/main/pyproject.toml)
[![license](https://img.shields.io/github/license/Wenfeng-Zhang/name-info)](LICENSE)

# name-info

将 VFX 文件名与序列帧路径解析成结构化信息。

`NameInfo` 接收一个文件名（或完整路径），判断帧号模式在哪、扩展名是什么，
以及如何把路径还原成序列模板。它不访问文件系统，因此可以直接用于尚不存在的路径。

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

English documentation: [README.md](README.md)。

## 特性

- 显式占位符：`%04d`、`%d`、`####`、`$F4`、`<UDIM>`、`%(UDIM)d`、`u<U>_v<V>`
- VFX 标准的四位帧号，如 `shot.1001.exr`
- UV Tile（`u1_v1`、`u10_v1`）与眼位标记（`%V`、`%v`）
- 版本号（`v001`、`v0028`）不会被误判为帧号
- 复合扩展名：`.exr.gz`、`.exr.bak`、`.bgeo.sc`、`.ass.gz`、`.tar.gz`
- `.tx` 纹理缓存（`.exr.tx` 的扩展名保留为 `tx`）
- 视频格式不做序列检测：`mp4`、`mov`、`avi`、`mkv`、`webm`
- 无运行时依赖；`__slots__` 让单实例占用更小

## 环境要求

- Python 3.7 及以上（测试矩阵覆盖 3.7 / 3.9 / 3.10 / 3.11）
- **不支持** Python 2：代码使用了类型注解与 f-string

## 安装

```console
python -m pip install .
```

开发用的可编辑安装（需要 `setuptools >= 61`）：

```console
python -m pip install -e .
```

如果 PyPI 访问缓慢或不通，改用清华大学镜像站：

```console
python -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

测试本身不需要任何第三方包。`tools/run_matrix.ps1` 会把该镜像写进每个
`.venvXX/pip.ini`，因此在这些环境里手动安装也会默认走镜像；
传 `-IndexUrl ''` 可恢复使用 pip 默认源。

## 属性说明

| 属性 | `d:/render/shot.1001.exr` 的取值 | 含义 |
| --- | --- | --- |
| `filename` | `'d:/render/shot.1001.exr'` | 规范化后的输入路径：反斜杠转 `/`，去掉首尾空白 |
| `dirname` | `'d:/render'` | `filename` 的目录部分 |
| `basename` | `'shot.1001.exr'` | `filename` 的文件名部分 |
| `name` | `'shot.'` | 移除主模式后的主体，保留相邻的原始分隔符 |
| `absname` | `'shot'` | `name` 去掉末尾点号 |
| `pattern` | `'1001'` | 匹配到的模式：字面数字，或占位符本身 |
| `padding` | `4` | 模式声明的填充宽度，未声明时为 `0` |
| `ext` | `'exr'` | 不带点号的扩展名，可能是复合形式 |
| `wild_name` | `'shot.????'` | 不含扩展名的问号通配名，位数与模式一致 |
| `other_pattern` | `None` | 同时出现的另一种模式（UV / 眼位 / 帧号），否则为 `None` |
| `template` | `'d:/render/shot.%04d.exr'` | 路径模板，每次访问时根据当前属性重算 |

所有属性都可写，`template` 由当前属性派生，因此会跟随手工改动：

```python
info.padding = 6
info.template    # 'd:/render/shot.%06d.exr'
```

注意：

- `pattern is None` 表示输入没有扩展名、完全没有解析；`pattern == ''` 表示
  解析过、但没有适用的序列模式。
- 没有声明宽度的占位符（`%d`、`$F`）与 UV Tile 的 `padding` 都是 `0`，
  后者的宽度信息体现在 `wild_name` 里。

## 解析优先级

| 优先级 | 规则 | 示例 |
| --- | --- | --- |
| 1 | 显式占位符 | `shot.%04d.exr`、`leg_02_<UDIM>_Height.tif`、`shot.$F4.exr` |
| 2 | 主体末尾的四位数字 | `shot.1001.exr` |
| 3 | UV Tile（主体以 `.<数字>` 结尾时跳过） | `tex_u10_v1.exr` |
| 4 | 版本号处理 | 从 `shot.v0028.1001.exr` 取到 `1001` |
| 5 | 任意数字，优先以 `1` 开头的那一个 | `asset_10001_8k.exr` |

正则细节与已知边界情况见
[docs/parsing-rules.zh-CN.md](docs/parsing-rules.zh-CN.md)。

## 命令行

不带参数时会打印 `name_info.examples.file_names` 中每一条示例的解析结果；
传入自己的路径即可直接检查任意命名：

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

## 示例

[`docs/examples.zh-CN.md`](docs/examples.zh-CN.md) 把同样的输出按功能展开
（占位符、UDIM、UV Tile、四位帧号、版本号、贴图与缓存、视频），
每条输入旁边就是真实输出。节选：

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

最后一条没有扩展名，因此不解析、输出为空。

## 测试

测试只依赖标准库。在项目根目录执行：

```console
python -m unittest discover
```

以下写法等价：

```console
python -m unittest discover -s tests
python tests/test_name_info.py
```

`tests/test_name_info.py` 自身会把项目根目录加入 `sys.path`，因此既不需要安装，
也不需要设置 `PYTHONPATH`。

跑完整的解释器矩阵（会在源码同级创建 `.venv37`、`.venv39`、`.venv310`、
`.venv311`，并在每个环境中执行一遍测试）：

```powershell
powershell -ExecutionPolicy Bypass -File tools/run_matrix.ps1
```

测试分为五层：

1. `SnapshotTests` —— 基于 `tests/fixtures/snapshot.json` 的逐字段快照，
   以及锁定解析行为的 sha256 指纹；两者都覆盖全部字段，且与平台无关。
2. `NameInfoTests` —— 针对具体行为的测试（填充宽度上限、复合扩展名、
   UV Tile、视频文件、属性可写性等）。
3. `CommandLineTests` —— 导入保持静默，`python -m name_info` 的输出与快照数据一致，
   能解析用户自己传入的文件名，并且会在进程内直接调用 `main()`。
4. `DocumentationTests` —— `docs/examples*.md` 与当前输出保持一致。
5. `PlatformPathTests` —— Windows 专属路径形式（`D:shot.1001.exr`、UNC 路径），
   按当前运行平台断言。

在有意变更解析行为后，重新生成快照并把新的指纹粘回测试模块：

```console
python tools/regenerate_snapshot.py
```

## 持续集成

`.github/workflows/tests.yml` 会在每次 push 和 pull request 时跑一遍测试：

- 系统：`ubuntu-22.04`、`windows-latest`、`macos-latest`
- Python：3.7 到 3.14（共 22 个组合）

其中两个组合是刻意排除的：`macos-latest` 是 arm64，而 `setup-python` 没有
3.7 / 3.8 的 arm64 构建。Linux 侧固定在 `ubuntu-22.04`，因为 24.04 上装不了
3.7（缺 OpenSSL 1.1）。

另有一个独立 job 构建 wheel，断言包里只有 `name_info/`，然后安装它、并从
一个无关目录调用 `python -m name_info`。

仓库地址是 <https://github.com/Wenfeng-Zhang/name-info>，CI 会在每次 push 与
pull request 时运行。如果是 fork 或全新克隆：

```console
git remote add origin git@github.com:<you>/name-info.git
git push -u origin main
```

## 目录结构

```text
name_info/
├── name_info/__init__.py         # 公开导出与 __version__
├── name_info/name_info.py        # NameInfo 实现
├── name_info/examples.py         # 演示与快照用例数据（非公开 API）
├── name_info/__main__.py         # python -m name_info 入口
├── tests/__init__.py             # 让 `unittest discover` 能从项目根发现测试
├── tests/test_name_info.py       # unittest 测试
├── tests/fixtures/snapshot.json  # 已批准的解析快照
├── tools/regenerate_snapshot.py  # 快照与指纹再生成
├── tools/build_example_docs.py   # 由代码生成 docs/examples*.md
├── tools/run_matrix.ps1          # 本地多解释器测试矩阵
├── .github/workflows/tests.yml   # CI：3 个系统 x Python 3.7-3.14 + wheel 冒烟
├── docs/parsing-rules.md         # 英文解析规则细节
├── docs/examples.zh-CN.md        # 每条示例旁边就是真实输出
└── pyproject.toml
```

## 许可

MIT —— 见 [LICENSE](LICENSE)。

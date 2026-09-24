# 解析规则

本文档按代码执行的顺序，说明 `NameInfo` 到底做了什么，也是
`tests/fixtures/snapshot.json` 中快照测试的依据。

## 1. 路径规范化

`__init__` 首先执行

```python
filename = input.strip().replace("\\", "/")
dirname, basename = os.path.split(filename)
```

因此混合斜杠和首尾空白不会进入解析逻辑。

`dirname` 与 `basename` 来自 `os.path`，所以有两种 Windows 风格路径在别处行为不同，
`PlatformPathTests` 对两种平台都做了断言：

* **盘符相对路径** —— `os.path.split("D:shot.1001.exr")` 在 Windows 上得到
  `("D:", "shot.1001.exr")`，在 POSIX 上得到 `("", "D:shot.1001.exr")`，
  `name`、`absname`、`wild_name`、`template` 都会随之不同。
* **盘符根目录下的文件** —— `os.path.split("D:/a.1001.exr")` 的 `dirname` 在 Windows
  上是 `"D:/"`，在 POSIX 上是 `"D:"`。只有 `dirname` 不同；
  `basename`、`absname`、`padding`、`template` 完全一致。

因为盘符根目录的 `dirname` 不具备跨平台一致性，给文件分组时请用 `absname` + `ext`
作为序列键，而不要直接用 `dirname` 字符串。这些输入都不在快照 fixture 里，
因此记录下来的每一条用例都与平台无关。

## 2. 扩展名解析（`_split_ext`）

按以下顺序尝试，均忽略大小写：

1. **复合后缀** —— 若文件名以 `.bgeo.sc`、`.bgeo.gz`、`.ass.gz`、`.vdb.sc`、
   `.vdb.gz`、`.tar.gz`、`.exr.gz`、`.exr.bak` 之一结尾，整个后缀成为 `ext`
   （去掉前导点，如 `exr.gz`）。
2. **`.tx` 缓存** —— 去掉 `.tx` 后，如果剩下的扩展名属于 `KNOWN_EXTS`，
   则连内层扩展名一起去掉，`ext` 为 `tx`。所以 `shot.1001.exr.tx` 得到主体
   `shot.1001` 与 `ext='tx'`；而 `shot.1001.foo.tx` 保留 `foo`（它不是已知图像格式）。
3. **没有点号** —— `ext` 为 `''`，解析立即结束：`name`、`pattern`、`absname`、
   `wild_name` 都保持 `None`。
4. **其余情况** —— 走标准 `os.path.splitext`，转小写并去掉点号。

`ext` 始终是小写；`filename` / `basename` 保留原始大小写。

两套点号约定是刻意并存的：

- `_IMG_EXTS`、`_GEO_EXTS`、`KNOWN_EXTS`、`SPECIAL_FORMATS` 中的值**带**前导点，
  因为它们要和 `os.path.splitext` 的返回值比较。
- `VIDEO_EXTS` 中的值**不带**点，因为它要和规范化后的 `ext` 比较。

## 3. 模式检测（`_find_pattern`）

类级正则有 `RE_PLACEHOLDER`、`RE_FOUR_DIGITS`、`RE_UV_TILE`、
`RE_UV_PLACEHOLDER`、`RE_VIEW_PLACEHOLDER`、`RE_FRAME_PLACEHOLDER`、
`RE_NUMBER`、`RE_VERSION_END`、`RE_VERSION_TOKEN`、`RE_FRAME_BEFORE_VERSION`、
`RE_DOT_NUMBER_END`；`RE_PADDING` 与 `RE_THOUSANDS` 是辅助正则。

| 优先级 | 条件 | 结果 |
| --- | --- | --- |
| 1 | `RE_PLACEHOLDER` 命中 `%\d*d`、`#+`、`<UDIM>`、`%(UDIM)d`、`u<U>_v<V>`、`$F\d*` | 该子串即 pattern |
| 2 | `RE_FOUR_DIGITS` 命中一个独立的四位数字，且其后再无数字直到结尾，或紧跟 `(数字)` | 该四位数字即 pattern |
| 3 | `RE_UV_TILE` 命中 `u(\d+)_v(\d+)`，且主体**不**以 `.<数字>` 结尾 | `u10_v1` 这类匹配即 pattern |
| 4 | `RE_VERSION_END` 命中结尾的 `v\d+` | 其紧前的数字（`\d+(?=\.v\d+$)`）成为 pattern，否则无 pattern |
| 5 | 任意数字，跳过 `v\d+` 记号 | 首个满足 `1\d{3}` 的数字优先，否则取最后一个数字 |

如果连数字都没有，就视为静态文件名：`pattern == ''` 且 `name == stem`。

## 4. 移除模式（`_strip_pattern`）

模式在**最后一次**出现处被移除，并保留一个相邻分隔符，因此
`leg_02_1021_Height.tif` 会变成 `leg_02_Height`：

| 切分形态 | 结果 |
| --- | --- |
| 模式位于末尾 | 前缀原样返回 |
| 前缀以 `.`、`_`、`-` 结尾 | `prefix + suffix.lstrip("._-")` |
| 后缀以 `.`、`_`、`-` 开头 | `prefix + suffix` |
| 两者都不满足 | `prefix + "_" + suffix` |

`absname` 等于 `name.rstrip(".")`。

## 5. 填充宽度与通配名

`_padding_width(pattern)` 返回声明的宽度：

| Pattern | `padding` |
| --- | --- |
| `<UDIM>`、`%(UDIM)d`（任意大小写） | 4 |
| `#`、`##`、`####` | 该串长度 |
| 字面数字（`1001`、`10001`） | 数字位数 |
| `%04d`、`$F4` | 声明的数字 |
| `%d`、`$F` | 0 |
| UV Tile（`u10_v1`） | 0 |

超过 `MAX_PADDING`（256）的宽度会抛 `ValueError`。

随后 `_wildcard(stem, pattern, padding)` 构建 `wild_name`，其中始终不含扩展名：

- padding 非 0 时：`pattern` 被替换为 `?` × `padding`（仅最后一次）→ `shot.????`
- `u<U>_v<V>`：所有出现处都替换为 `u?_v?`，保留大小写 → `a_u?_v?_b_u?_v?`
- UV Tile：每个坐标按其位数生成 `?`，保留大小写 → `u10_v1` 变成 `u??_v?`
- 其余情况（`%d` 这类未声明宽度的占位符）：主体原样返回

## 6. 模板

`template` 是 property，每次访问都根据当前属性重算。没有 pattern 或 padding 时
原样返回 `filename`，因此静态文件名会原样往返。其余情况：

- `<UDIM>` / `%(UDIM)d` 归一为 `<UDIM>`（任意大小写）
- 字面数字变成 `%0Nd`，其中 `N == padding`
- 其它占位符（`$F4`、`%04d`、`u<U>_v<V>`）按原样保留

只替换主体中最后一次出现的位置，扩展名部分原样保留，所以
`shot.1001.TIF.TX` 得到 `shot.%04d.TIF.TX`。

## 7. 视频文件

若 `ext` 属于 `VIDEO_EXTS`，则完全不进行模式检测：`name` 为主体，
`pattern` 为 `''`，`template` 原样返回 `filename`。

## 8. 已知限制

以下都是启发式规则的必然结果，且全部被快照测试覆盖。

- `$F\d*` 会命中单独的 `$F`，因此 `cache_$Frame.exr` 会解析成 pattern `$F`、
  `name == 'cache_rame'`；`$Foo` 同理。
- `%\d*d` 会命中普通单词里的 `%d`：`pct_100%discount.exr` 得到 pattern `%d`、
  `name == 'pct_100_iscount'`。
- `#+` 会命中任意 `#`，因此 `note_10#_v1.exr` 的 pattern 是 `#`。
- 四位数字规则只在"其后到结尾只剩非数字"时生效，所以
  `plate_1001_2001.exr` 取到**最后**一个符合条件的数字（`2001`），而
  `a_1001_b_1002_8k.exr` 落到规则 5 取到 `1001`。
- `padding == 0` 有两种含义：对 `%d`/`$F` 表示"未声明宽度"，对 `u1_v1`
  表示"UV Tile"。UV Tile 的宽度信息保存在 `wild_name` 里。
- `pattern is None`（无扩展名、未解析）与 `pattern == ''`（已解析、无模式）
  是两种不同状态，需要区分时请用 `is None` 判断。
- `.tx` 只剥离一层内层扩展名。

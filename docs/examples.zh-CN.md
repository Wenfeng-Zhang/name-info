# 解析示例

下面每一块都是 `python -m name_info` 的真实输出：第一行是输入，随后是
`NameInfo` 解析出的各个属性。输入与 `name_info/examples.py` 完全一致，
本地跑 `python -m name_info` 就能看到同样的结果，也可以传入自己的路径。
规则细节见 [parsing-rules.zh-CN.md](parsing-rules.zh-CN.md)。

同一份内容另有英文版：[examples.md](examples.md)。


## 1. 显式帧占位符

`%04d`、`####`、`$F4` 的优先级高于所有数字启发式规则，占位符前后的文本都会保留（包括末尾的 `_beauty`）。

```text
d:/render/testA_diffuse.%04d.exr
name='testA_diffuse.', pattern='%04d', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse.????'

d:/render/testA1001_diffuse.%04d.exr
name='testA1001_diffuse.', pattern='%04d', ext='exr', absname='testA1001_diffuse', padding=4, wild_name='testA1001_diffuse.????'

d:/render/testA_diffuse%04d.exr
name='testA_diffuse', pattern='%04d', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse????'

d:/render/testA_diffuse_%04d_beauty.exr
name='testA_diffuse_beauty', pattern='%04d', ext='exr', absname='testA_diffuse_beauty', padding=4, wild_name='testA_diffuse_????_beauty'

d:/render/testA_diffuse_####_beauty.exr
name='testA_diffuse_beauty', pattern='####', ext='exr', absname='testA_diffuse_beauty', padding=4, wild_name='testA_diffuse_????_beauty'

d:/render/testA_diffuse.####.exr
name='testA_diffuse.', pattern='####', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse.????'

d:/render/testA_diffuse####.exr
name='testA_diffuse', pattern='####', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse????'

d:/render/testA_diffuse.abc.$F4.exr
name='testA_diffuse.abc.', pattern='$F4', ext='exr', absname='testA_diffuse.abc', padding=4, wild_name='testA_diffuse.abc.????'

d:/render/testA_diffuse.abc.layer.$F4.exr
name='testA_diffuse.abc.layer.', pattern='$F4', ext='exr', absname='testA_diffuse.abc.layer', padding=4, wild_name='testA_diffuse.abc.layer.????'

d:/render/testA_diffuse.$F4.exr
name='testA_diffuse.', pattern='$F4', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse.????'

d:/render/testA_$F4_diffuse.exr
name='testA_diffuse', pattern='$F4', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_????_diffuse'

d:/render/testA_diffuse$F4.exr
name='testA_diffuse', pattern='$F4', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse????'
```

## 2. UDIM 贴图

`<UDIM>`、`<udim>`、`%(UDIM)d` 在 `template` 里统一归一为 `<UDIM>`，贴图后缀在 UDIM 前后都不影响识别。

```text
d:/render/testA<UDIM>_diffuse.exr
name='testA_diffuse', pattern='<UDIM>', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA????_diffuse'

d:/render/testA_diffuse10.<UDIM>.exr
name='testA_diffuse10.', pattern='<UDIM>', ext='exr', absname='testA_diffuse10', padding=4, wild_name='testA_diffuse10.????'

d:/render/testA_diffuse.%(UDIM)d.exr
name='testA_diffuse.', pattern='%(UDIM)d', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse.????'

d:/render/testA_diffuse%(UDIM)d.exr
name='testA_diffuse', pattern='%(UDIM)d', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse????'

d:/tex/testA10_mask_<UDIM>_8k.jpg
name='testA10_mask_8k', pattern='<UDIM>', ext='jpg', absname='testA10_mask_8k', padding=4, wild_name='testA10_mask_????_8k'

d:/tex/testA_mask_<UDIM>_8k.jpg
name='testA_mask_8k', pattern='<UDIM>', ext='jpg', absname='testA_mask_8k', padding=4, wild_name='testA_mask_????_8k'

d:/tex/testA_leg_02_<UDIM>_Height.tif
name='testA_leg_02_Height', pattern='<UDIM>', ext='tif', absname='testA_leg_02_Height', padding=4, wild_name='testA_leg_02_????_Height'
```

## 3. UV Tile

实际的 UV Tile（`u1_v1`、`u10_v1`）与 `u<U>_v<V>` 占位符都保留大小写，`wild_name` 里每个坐标的位数独立（`u10_v1` 变成 `u??_v?`）。

```text
d:/tex/testA_diffuseu1_v1.exr
name='testA_diffuse', pattern='u1_v1', ext='exr', absname='testA_diffuse', padding=0, wild_name='testA_diffuseu?_v?'

d:/tex/testA_u1_v1_diffuse.exr
name='testA_diffuse', pattern='u1_v1', ext='exr', absname='testA_diffuse', padding=0, wild_name='testA_u?_v?_diffuse'

d:/tex/testA_diffuse.u1_v1.1.exr
name='testA_diffuse.u1_v1.', pattern='1', ext='exr', absname='testA_diffuse.u1_v1', padding=1, wild_name='testA_diffuse.u1_v1.?'

d:/tex/testA_diffuse.u1_v1.exr
name='testA_diffuse.', pattern='u1_v1', ext='exr', absname='testA_diffuse', padding=0, wild_name='testA_diffuse.u?_v?'

d:/tex/testA_u10_v1.exr
name='testA_', pattern='u10_v1', ext='exr', absname='testA_', padding=0, wild_name='testA_u??_v?'

d:/tex/testA_diffuse.u<U>_v<V>.exr
name='testA_diffuse.', pattern='u<U>_v<V>', ext='exr', absname='testA_diffuse', padding=0, wild_name='testA_diffuse.u?_v?'

d:/tex/testA_diffuseu<U>_v<V>.exr
name='testA_diffuse', pattern='u<U>_v<V>', ext='exr', absname='testA_diffuse', padding=0, wild_name='testA_diffuseu?_v?'

d:/tex/testA_u<U>_v<V>diffuse.exr
name='testA_diffuse', pattern='u<U>_v<V>', ext='exr', absname='testA_diffuse', padding=0, wild_name='testA_u?_v?diffuse'

d:/tex/testA_U<U>_V<V>.exr
name='testA_', pattern='U<U>_V<V>', ext='exr', absname='testA_', padding=0, wild_name='testA_U?_V?'
```

## 4. 四位帧号

VFX 最常见的格式：主体末尾独立的四位数字。注意紧邻帧号的分隔符会被保留（`leg_02_1021_Height` → `leg_02_Height`）。

```text
d:/render/testA_diffuse_v0028.1001.exr
name='testA_diffuse_v0028.', pattern='1001', ext='exr', absname='testA_diffuse_v0028', padding=4, wild_name='testA_diffuse_v0028.????'

d:/render/testA_diffuse1001.exr
name='testA_diffuse', pattern='1001', ext='exr', absname='testA_diffuse', padding=4, wild_name='testA_diffuse????'

d:/render/testA.beauty1001.exr
name='testA.beauty', pattern='1001', ext='exr', absname='testA.beauty', padding=4, wild_name='testA.beauty????'

d:/render/show_20260924_asset.exr
name='show_asset', pattern='20260924', ext='exr', absname='show_asset', padding=8, wild_name='show_????????_asset'

d:/render/shot.1001.1001.ext
name='shot.1001.', pattern='1001', ext='ext', absname='shot.1001', padding=4, wild_name='shot.1001.????'

d:/tex/testA_mask_1001_8k_<UDIM>.jpg
name='testA_mask_1001_8k_', pattern='<UDIM>', ext='jpg', absname='testA_mask_1001_8k_', padding=4, wild_name='testA_mask_1001_8k_????'

d:/tex/testA_mask_1001_8k.jpg
name='testA_mask_8k', pattern='1001', ext='jpg', absname='testA_mask_8k', padding=4, wild_name='testA_mask_????_8k'

d:/tex/testA.mask_1001_8k.jpg
name='testA.mask_8k', pattern='1001', ext='jpg', absname='testA.mask_8k', padding=4, wild_name='testA.mask_????_8k'

d:/tex/testA_leg_02_1021_Height.tif
name='testA_leg_02_Height', pattern='1021', ext='tif', absname='testA_leg_02_Height', padding=4, wild_name='testA_leg_02_????_Height'

d:/tex/testA_leg_02.1021_Height.tif
name='testA_leg_02.Height', pattern='1021', ext='tif', absname='testA_leg_02.Height', padding=4, wild_name='testA_leg_02.????_Height'

d:/tex/testA_leg_xy.02_1021_Height.tif
name='testA_leg_xy.02_Height', pattern='1021', ext='tif', absname='testA_leg_xy.02_Height', padding=4, wild_name='testA_leg_xy.02_????_Height'

d:/tex/testA_leg_xy.1021_Height.tif
name='testA_leg_xy.Height', pattern='1021', ext='tif', absname='testA_leg_xy.Height', padding=4, wild_name='testA_leg_xy.????_Height'

d:/tex/testA_leg_xy._1021_Height.tif
name='testA_leg_xy._Height', pattern='1021', ext='tif', absname='testA_leg_xy._Height', padding=4, wild_name='testA_leg_xy._????_Height'

d:/tex/testA_leg_02_<UDIM>(1).tif
name='testA_leg_02_(1)', pattern='<UDIM>', ext='tif', absname='testA_leg_02_(1)', padding=4, wild_name='testA_leg_02_????(1)'

d:/tex/testA_leg_02_1001(1).tif
name='testA_leg_02_(1)', pattern='1001', ext='tif', absname='testA_leg_02_(1)', padding=4, wild_name='testA_leg_02_????(1)'

d:/tex/testA_1234_mask_4K_1001.jpg
name='testA_1234_mask_4K_', pattern='1001', ext='jpg', absname='testA_1234_mask_4K_', padding=4, wild_name='testA_1234_mask_4K_????'
```

## 5. 版本号与静态名

结尾的 `v001` 是版本号而不是帧号，因此不会识别出序列模式，`template` 原样返回路径。最后一条完全没有扩展名，所以输出为空。

```text
d:/render/testA_diffusev001.exr
name='testA_diffusev001', pattern='', ext='exr', absname='testA_diffusev001', padding=0, wild_name='testA_diffusev001'

d:/render/shot_v002_final.exr
name='shot_v002_final', pattern='', ext='exr', absname='shot_v002_final', padding=0, wild_name='shot_v002_final'

d:/render/shot_v1001_diff.exr
name='shot_v1001_diff', pattern='', ext='exr', absname='shot_v1001_diff', padding=0, wild_name='shot_v1001_diff'

d:/render/testA_0110_key_master_v009.exr
name='testA_0110_key_master_v009', pattern='', ext='exr', absname='testA_0110_key_master_v009', padding=0, wild_name='testA_0110_key_master_v009'

d:/render/testA

```

## 6. 贴图、缓存与复合扩展名

复合后缀（`.bgeo.sc`、`.ass.gz`、`.exr.gz`、`.exr.bak`）整体保留；`.tx` 缓存会把内层图像扩展名剥掉，只留 `tx` 作为扩展名。

```text
d:/render/testA.1001.exr.gz
name='testA.', pattern='1001', ext='exr.gz', absname='testA', padding=4, wild_name='testA.????'

d:/render/testA.1001.exr.bak
name='testA.', pattern='1001', ext='exr.bak', absname='testA', padding=4, wild_name='testA.????'

d:/tex/testA_154_022_leaf_diffuse_02.jpg
name='testA_154_022_leaf_diffuse_', pattern='02', ext='jpg', absname='testA_154_022_leaf_diffuse_', padding=2, wild_name='testA_154_022_leaf_diffuse_??'

d:/cache/testA_154_022_leaf_.diffuse_02.bgeo.sc
name='testA_154_022_leaf_.diffuse_', pattern='02', ext='bgeo.sc', absname='testA_154_022_leaf_.diffuse_', padding=2, wild_name='testA_154_022_leaf_.diffuse_??'

d:/cache/testA_154_022_leaf_.diffuse_02.ass.gz
name='testA_154_022_leaf_.diffuse_', pattern='02', ext='ass.gz', absname='testA_154_022_leaf_.diffuse_', padding=2, wild_name='testA_154_022_leaf_.diffuse_??'

d:/tex/testA_body_coat_8k_1001_Raw_scene-linear Rec 709_sRGB.tif.tx
name='testA_body_coat_8k_Raw_scene-linear Rec 709_sRGB', pattern='1001', ext='tx', absname='testA_body_coat_8k_Raw_scene-linear Rec 709_sRGB', padding=4, wild_name='testA_body_coat_8k_????_Raw_scene-linear Rec 709_sRGB'

d:/tex/testA_body_coat_8k_<UDIM>_Raw_scene-linear Rec 709_sRGB.tif.tx
name='testA_body_coat_8k_Raw_scene-linear Rec 709_sRGB', pattern='<UDIM>', ext='tx', absname='testA_body_coat_8k_Raw_scene-linear Rec 709_sRGB', padding=4, wild_name='testA_body_coat_8k_????_Raw_scene-linear Rec 709_sRGB'

d:/tex/testA_cloth_col_4k.<udim>_sRGB_scene-linear Rec 709_sRGB.tif.tx
name='testA_cloth_col_4k.sRGB_scene-linear Rec 709_sRGB', pattern='<udim>', ext='tx', absname='testA_cloth_col_4k.sRGB_scene-linear Rec 709_sRGB', padding=4, wild_name='testA_cloth_col_4k.????_sRGB_scene-linear Rec 709_sRGB'

d:/tex/testA_cloth_col_4k.1001_sRGB_scene-linear Rec 709_sRGB.tif.tx
name='testA_cloth_col_4k.sRGB_scene-linear Rec 709_sRGB', pattern='1001', ext='tx', absname='testA_cloth_col_4k.sRGB_scene-linear Rec 709_sRGB', padding=4, wild_name='testA_cloth_col_4k.????_sRGB_scene-linear Rec 709_sRGB'
```

## 7. 眼位标记与视频

`%V` 会作为 `other_pattern` 与帧占位符并存记录；视频文件则完全不做模式检测。

```text
d:/render/testA.%04d.%V.exr
name='testA.%V', pattern='%04d', ext='exr', absname='testA.%V', padding=4, wild_name='testA.????.%V'

d:/render/testA2_Bokeh_DOF_04.mp4
name='testA2_Bokeh_DOF_04', pattern='', ext='mp4', absname='testA2_Bokeh_DOF_04', padding=0, wild_name='testA2_Bokeh_DOF_04'
```

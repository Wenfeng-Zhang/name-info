#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Demo and snapshot inputs, deliberately outside the public API.

The list serves two purposes:

* the default input of ``python -m name_info`` when it is called without arguments;
* the case source of the snapshot tests and ``tools/regenerate_snapshot.py``.

Import it explicitly when needed: ``from name_info.examples import file_names``.
"""

file_names = [
    'd:/render/testA_diffuse.%04d.exr',
    'd:/render/testA1001_diffuse.%04d.exr',
    'd:/render/testA_diffuse%04d.exr',
    'd:/render/testA_diffuse_%04d_beauty.exr',
    'd:/render/testA_diffuse_####_beauty.exr',
    'd:/render/testA_diffuse.####.exr',
    'd:/render/testA_diffuse####.exr',
    'd:/render/testA_diffuse_v0028.1001.exr',
    'd:/render/testA_diffuse1001.exr',
    'd:/render/testA<UDIM>_diffuse.exr',
    'd:/render/testA_diffuse10.<UDIM>.exr',
    'd:/render/testA_diffuse.%(UDIM)d.exr',
    'd:/render/testA_diffuse%(UDIM)d.exr',
    'd:/render/testA_diffuse.abc.$F4.exr',
    'd:/render/testA_diffuse.abc.layer.$F4.exr',
    'd:/render/testA_diffuse.$F4.exr',
    'd:/render/testA_$F4_diffuse.exr',
    'd:/render/testA_diffuse$F4.exr',
    'd:/render/testA_diffusev001.exr',
    'd:/render/testA.beauty1001.exr',
    'd:/render/testA.%04d.%V.exr',
    'd:/render/testA.1001.exr.gz',
    'd:/render/testA.1001.exr.bak',
    'd:/render/shot.1001.1001.ext',
    'd:/render/shot_v002_final.exr',
    'd:/render/shot_v1001_diff.exr',
    'd:/render/show_20260924_asset.exr',
    'd:/render/testA',
    'd:/render/testA_0110_key_master_v009.exr',
    'd:/render/testA2_Bokeh_DOF_04.mp4',
    'd:/tex/testA_154_022_leaf_diffuse_02.jpg',
    'd:/cache/testA_154_022_leaf_.diffuse_02.bgeo.sc',
    'd:/cache/testA_154_022_leaf_.diffuse_02.ass.gz',
    'd:/tex/testA10_mask_<UDIM>_8k.jpg',
    'd:/tex/testA_mask_1001_8k_<UDIM>.jpg',
    'd:/tex/testA_mask_1001_8k.jpg',
    'd:/tex/testA.mask_1001_8k.jpg',
    'd:/tex/testA_mask_<UDIM>_8k.jpg',
    'd:/tex/testA_leg_02_1021_Height.tif',
    'd:/tex/testA_leg_02.1021_Height.tif',
    'd:/tex/testA_leg_xy.02_1021_Height.tif',
    'd:/tex/testA_leg_xy.1021_Height.tif',
    'd:/tex/testA_leg_xy._1021_Height.tif',
    'd:/tex/testA_leg_02_<UDIM>_Height.tif',
    'd:/tex/testA_leg_02_<UDIM>(1).tif',
    'd:/tex/testA_leg_02_1001(1).tif',
    'd:/tex/testA_1234_mask_4K_1001.jpg',
    'd:/tex/testA_body_coat_8k_1001_Raw_scene-linear Rec 709_sRGB.tif.tx',
    'd:/tex/testA_body_coat_8k_<UDIM>_Raw_scene-linear Rec 709_sRGB.tif.tx',
    'd:/tex/testA_cloth_col_4k.<udim>_sRGB_scene-linear Rec 709_sRGB.tif.tx',
    'd:/tex/testA_cloth_col_4k.1001_sRGB_scene-linear Rec 709_sRGB.tif.tx',
    'd:/tex/testA_diffuseu1_v1.exr',
    'd:/tex/testA_u1_v1_diffuse.exr',
    'd:/tex/testA_diffuse.u1_v1.1.exr',
    'd:/tex/testA_diffuse.u1_v1.exr',
    'd:/tex/testA_diffuse.u<U>_v<V>.exr',
    'd:/tex/testA_diffuseu<U>_v<V>.exr',
    'd:/tex/testA_u<U>_v<V>diffuse.exr',
    'd:/tex/testA_u10_v1.exr',
    'd:/tex/testA_U<U>_V<V>.exr',
]

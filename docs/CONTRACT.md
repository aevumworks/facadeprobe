# Data contract v1

This contract describes the v0.1.0 resource, not arbitrary architectural datasets.

The eight window instances are `101..108`, the door is `201`. Walls/trim use `1`, ground `6`, roof/parapet `7`. Balcony groups are `401`, `402`; screen/slats and opaque panel are `501`, `502`. Background is instance `0`. Multiple mesh objects can belong to one semantic instance. See each case's `instance_mapping` in `manifest.json` for object membership.

Semantic classes are in `classes.json`. The PNG files store numeric IDs, not palette colors. Read without byte reduction:

```python
import json
from pathlib import Path
import numpy as np
from PIL import Image

view = Path("data/views/screen/front")
instance = np.asarray(Image.open(view / "instance.png"), dtype=np.uint16)
semantic = np.asarray(Image.open(view / "semantic.png"), dtype=np.uint8)
depth_z = np.load(view / "depth-z.npy", allow_pickle=False)
camera = json.loads((view / "camera.json").read_text(encoding="utf-8"))
assert (instance == 101).sum() == 499

world_point = np.array([0.0, 0.0, 4.4, 1.0])
cv = np.asarray(camera["world_to_camera_cv"]) @ world_point
hom = np.asarray(camera["K"]) @ cv[:3]
uv = hom[:2] / hom[2]  # image-corner origin; pixel centres are x+.5, y+.5
```

`annotations.json` contains visible surface areas and integer visible bounding boxes. Bbox `[x,y,w,h]` includes pixels `x..x+w-1`, `y..y+h-1`. A narrow surviving strip can have a nonzero area; "visible" means at least one labeled pixel, not a thresholded detector decision. A bbox is not an amodal box and does not label occluder pixels inside it as window material.

Depth NPY is `(height,width)`, float32 metres along camera +Z. The original EXR has one float channel `Value.V`; on the verified Blender 5.2 runtime it already equals camera Z. Background EXR is `1e10`, converted to NaN in the NPY. Do not multiply by a ray normalization factor. The preview is clamped to 0..35 m and is not a depth encoding.

All JSON numbers use ordinary decimal values. World-to-camera and camera-to-world matrices are 4×4, row-major nested arrays acting on column homogeneous vectors. K is 3×3. Distortion is `[0,0,0,0,0]`. World is right-handed X/right, Z/up, front/−Y; OpenCV camera is X/right, Y/down, Z/forward. Intrinsics are defined for native 960×720, not resized web images.

The same geometry IDs and camera poses are used across conditions. Paired hidden fraction is `1 - area_condition / area_clean` for the same instance and camera. Its denominator is the clean view's visible pixels, not the full physical surface area or a model score. No random train/test partition is appropriate for these near-duplicate views.

## Native glTF / GLB basis

The JSON world above and the editable Blender scene are **Z-up**. The GLB was exported with `export_yup=True`, so a normal glTF engine sees a **Y-up** world. A dataset point `[X,Y,Z]` becomes glTF `[X,Z,-Y]`; the inverse is `[x,y,z]` → dataset `[x,-z,y]`.

For column homogeneous vectors, the supplied matrices are:

```text
M_gltf_from_dataset =          M_dataset_from_gltf =
 [1  0  0  0]                  [1  0  0  0]
 [0  0  1  0]                  [0  0 -1  0]
 [0 -1  0  0]                  [0  1  0  0]
 [0  0  0  1]                  [0  0  0  1]
```

Use native **glTF world** positions (after the glTF node transform), not mesh-local coordinates:

```python
cv = world_to_camera_cv @ M_dataset_from_gltf @ point_gltf_world
uv_h = K @ cv[:3]
uv = uv_h[:2] / uv_h[2]
```

Do not apply JSON `world_to_camera_cv` directly to Y-up GLB world coordinates. The front camera is approximately `[0,-20,5.6]` in dataset world and `[0,5.6,20]` in native glTF world. The common look-at point `[0,0,4.4]` becomes `[0,4.4,0]`; with the front camera and shipped K it projects to approximately `[480,360]` pixels in both correctly converted paths.

Native glTF camera **local** axes are +X/right, +Y/up and viewing −Z. JSON OpenCV camera axes are +X/right, +Y/down and +Z/forward. These camera-axis conventions are distinct from the world-basis rotation. The local conversion is `F = diag(1,-1,-1,1)`:

```text
camera_to_world_gltf_local = M_gltf_from_dataset @ camera_to_world_cv @ F
world_to_camera_cv_from_gltf = F @ inverse(camera_to_world_gltf_local)
                            = world_to_camera_cv @ M_dataset_from_gltf
```

The conversion matrices are present in `manifest.json:model_coordinates` and in the editable fixture configuration. `gltf-coordinate-validation.json` parses native GLB node matrices/TRS and checks all 12 camera poses and projected opening points **without Blender reimport**, which would automatically convert Y-up back to Z-up.

Source `.blend` files contain no external texture references. Render/compositor output paths are relative to the source file. GLB includes materials, instance/class extras and camera poses in this converted native glTF basis; it does not encode an IFC ontology or reproduce all Blender render settings.

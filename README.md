# FacadeProbe

An editable architectural facade fixture for checking visible labels, camera projection and occlusion in building computer vision.

**One original building, three paired conditions, four fixed cameras: 12 real Blender renders.** The resource includes editable `.blend` scenes, reimported `.glb` models, RGB, semantic/instance masks, camera-Z depth, OpenCV camera matrices and visible-instance annotations. A local HTML viewer lets you inspect the actual data without a server.

[中文](README.zh-CN.md) · [Download v0.1.0](https://github.com/aevumworks/facadeprobe/releases/tag/v0.1.0)

![Actual FacadeProbe viewer and rendered labels](https://github.com/aevumworks/facadeprobe/releases/download/v0.1.0/preview.png)

This is a **small synthetic debugging resource**, not a training benchmark, real engineering BIM or evidence of recognition accuracy/generalization.

## Open the ready-made resource

1. Download and unpack `facadeprobe-0.1.0-resource.zip` from Releases.
2. Open `data/index.html` in a browser. No installation or server is required for viewing.
3. Switch condition, camera and RGB / semantic / overlay / depth. Choose a window or door to see its real mask area and visible bounding box. Download links point to the corresponding scene, model, camera and labels inside the package.
4. Open `data/scenes/*.blend` in **Blender 5.2**, or import the `.glb` into a compatible 3D application. Calibrated computer-vision cameras are defined by `camera.json`; do not infer intrinsics from a viewer's display size.

The root LICENSE covers the independently created code, geometry, materials, renders and annotations. No external meshes, textures, fonts or customer drawings are included.

## What is paired

The same building geometry and camera IDs are shared between:

| Condition | Added geometry |
| --- | --- |
| `clean` | No foreground occluder |
| `balcony` | Two projecting balcony slabs and railings |
| `screen` | A foreground slatted screen and opaque test panel |

Cameras: `front`, `left`, `right`, `high`. The wall body is 12.0 m wide, 9.2 m high and 4.0 m deep, with **8 window instances and 1 door**; roof/parapet geometry extends above it. The occluders are controlled test geometry, not construction details. Units are metres. RGB uses Cycles CPU, 12 samples, denoising, 960×720; masks are un-antialiased geometry passes.

For example, window **101**, same `front` camera: **9,925 visible pixels** in `clean`, **499** in `screen`, a **94.972% reduction relative to that clean view**. This measures visible mask area, not model detection accuracy. All nine opening instances still exist in the scene; visibility is view-dependent.

## Files and conventions

```text
data/
  index.html                    offline data viewer
  manifest.json                 fixture, renderer, stable IDs, file paths
  classes.json                  7 foreground classes + background
  validation.json               geometry/ray checks and paired visible areas
  import-validation.json         actual .blend reopen / .glb import results
  scenes/{condition}.blend       editable source, relative render paths
  scenes/{condition}.glb         meshes, materials, instance/class extras, camera poses
  views/{condition}/{camera}/
    rgb.png                     8-bit RGB, 960×720
    semantic.png                uint8 IDs (0..7), not the colored preview
    instance.png                uint16 stable IDs; load without 8-bit conversion
    semantic-color.png          class-colored preview
    overlay.png                 RGB / class overlay for inspection
    depth-z.npy                 float32 optical-axis Z in metres; background NaN
    depth-preview.png           fixed 0..35 m visualization, not numeric depth
    camera.json                 K, world_to_camera_cv, camera_to_world_cv
    annotations.json            visible pixels and visible bbox per instance
    geometry-checks.json        independent Blender projection / scene-ray references
    raw-instance/instance.exr   original float Object Index pass
    raw-depth/depth.exr         original Blender 5.2 Depth pass
```

- World: right-handed, X along the facade, Z up; front direction is −Y.
- Camera: **OpenCV X right, Y down, Z forward**. `p_cv = world_to_camera_cv @ [X,Y,Z,1]`; `u,v = (K @ p_cv[:3])[:2] / p_cv[2]`.
- Image upper-left corner is `(0,0)`; pixel `(x,y)` is sampled at `(x+0.5,y+0.5)`. No lens distortion.
- Depth is **camera Z**, not Euclidean ray range. This was empirically checked against first-hit world positions transformed into each camera. The shipped original pass is already camera Z on Blender 5.2.
- Windows include their opaque inset surface, frame, mullion and transom. They do **not** simulate physical glass transmission. The sill is wall/trim.
- Masks label visible surfaces only. Invisible instances have area 0 and bbox `null`; no amodal completion is invented.
- Bounding boxes are integer `[x,y,width,height]` around visible pixels. A box does not mean its whole interior is window material.
- `.glb` is an interchange model, not a pixel-identical Blender renderer. Camera JSON is authoritative for CV projection; original renderer passes remain in the resource.

See [the data contract](docs/CONTRACT.md) for IDs and loading examples.

## Reproduce from source

Requirements: **Blender 5.2**, Python 3.10+ for postprocessing, NumPy, Pillow, OpenEXR. The actual run used Windows 11, Blender 5.2.0 LTS, Python 3.14.7, NumPy 2.5.4, Pillow 12.3.0, OpenEXR 3.5.3. No BlenderProc installation is required.

Create a local Python environment and install `requirements.txt`, then run from this repository root:

```sh
blender --background --factory-startup --python-exit-code 1 --python scripts/generate.py -- --output data
python scripts/process_validate.py data
blender --background --factory-startup --python-exit-code 1 --python scripts/verify_import.py -- data
python scripts/build_viewer.py data
```

`data` must not already exist. Use a new output directory to regenerate. All commands operate in the new background Blender process; do not run the generator inside a working scene you want to preserve. The generator calls factory reset inside its own process for each condition. It does not control an existing Blender UI or change global preferences.

Use `--width`, `--height`, `--samples`, `--threads`, `--cases`, `--views` after the generator's `--` for a reduced render while developing. The ready-made resource and offline viewer are built for the complete default 3×4 set. The source JSON is editable, but changed geometry/camera configurations need fresh validation; the shipped results do not certify your edits.

## Actual validation

All **12 views** passed encoded PNG readback, ID/class consistency, dimensions, visible-area/bbox checks and independent interior scene-ray comparison: **4,894 checked ray samples, 0 label mismatches**. Projection was checked against Blender's own projection of known 3D points; maximum absolute error was **0.0000872 px**. Interior building depth was checked against ray-hit positions; maximum absolute difference was **0.0001851 m**. Boundary pixels are excluded from ray checks using a 5×5 constant-instance neighborhood; this is not a claim about subpixel/antialiasing perfection at every edge.

Negative controls shifting the principal point by 12 px, vertically flipping labels/depth together, or multiplying depth by 1,000 were rejected. Three `.blend` files were reopened, three `.glb` files were imported into a fresh Blender scene; mesh counts, instance/class IDs, world AABBs and camera poses were checked. See the actual reports in the resource and [validation notes](docs/VALIDATION.md).

Viewer checks cover real metadata values, condition/view/channel switches, visible boxes, instance selection, local file links, keyboard details and desktop/narrow layouts. Narrow screenshots are browser emulation, not physical-phone acceptance. macOS/Linux and third-party GLB importers were not runtime-tested.

## Scope and related work

The controlled pairs are useful for checking mask orientation, camera axes, metre/mm mistakes, stable cross-view IDs and visible-vs-hidden annotations before running a larger architectural CV pipeline. They do not establish real-world performance, dataset diversity, structural compliance, production photorealism or an IFC/BIM ontology. One building and one lighting setup cannot serve as an independent train/test population. No train/validation/test split or model score is supplied.

[BlenderProc](https://github.com/DLR-RM/BlenderProc) offers a general synthetic-rendering pipeline. [Blender Facade Synthesis](https://github.com/LeoAKALiu/blender-facade-synthesis) describes a larger facade training-data workflow. FacadeProbe independently creates a smaller inspectable fixture; it does not claim a missing market category or copy either implementation.

## License

[MIT](LICENSE), for both the original code and original resource assets. Blender, NumPy, Pillow and OpenEXR are external tools/dependencies under their own licenses; none of their binaries or source distributions are bundled. See [v0.1.0 release notes](CHANGELOG.md).

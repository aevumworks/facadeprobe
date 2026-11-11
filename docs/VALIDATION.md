# v0.1.0 validation

Actual platform: Windows 11 Enterprise 10.0.26200; Blender 5.2.0 LTS (`fbe6228777e7`), CPU Cycles, 12 samples, 4 threads; 960×720. Postprocessing used CPython 3.14.7, NumPy 2.5.4, Pillow 12.3.0, OpenEXR 3.5.3. Date: 2026-11-11, Asia/Shanghai.

## Pixel and geometry checks

- 3 conditions × 4 fixed cameras = 12 real RGB/Index/Depth renders.
- All original object-index values were integral and declared by the scene; semantic classes were mapped from those IDs.
- Numeric instance/semantic PNGs were loaded back after encoding and compared exactly to the source arrays. Dimensions, per-instance area and visible bounding boxes were checked.
- 4,894 interior pixel samples were compared with independent `scene.ray_cast` hits computed through the exported camera convention: zero instance/class mismatches. A 5×5 constant-instance patch excludes subpixel boundaries.
- Known 3D opening reference points were projected through exported OpenCV matrices and compared with Blender's projection. Largest absolute coordinate difference: `0.0000871755` px; acceptance threshold `0.001` px.
- Interior wall/window/door/roof depth samples were compared with ray-hit world positions transformed into camera +Z. Largest absolute difference: `0.000185013` m; explicit acceptance threshold `0.03` m. Actual errors are reported per view; this is not a physical reconstruction accuracy result.
- Added occluders were checked not to increase window/door visible pixel counts compared with the same clean camera.

Negative controls were actually executed in memory: 12 px principal-point shift, simultaneous vertical flip of both labels and depth, and depth scaled by 1000. All were rejected. These do not mutate the release data.

## Editable source and interchange

All three `.blend` files were reopened by Blender. Mesh counts: clean 138, balcony 192, screen 157; four cameras per condition. The three GLBs were imported into separate fresh scenes. Instance/class extras, mesh counts, world-space AABBs and camera poses matched; maximum AABB difference was 0 m, maximum camera matrix element difference `1.78814e-7`. Relative render/compositor paths were checked in the `.blend` files.

GLB importer checks used Blender only. No claim is made about other 3D applications or pixel-identical GLB rendering.

The GLBs use native glTF Y-up; JSON world uses dataset/Blender Z-up. A separate `verify_gltf_coordinates.py` parses native GLB node JSON, composes parent/TRS matrices, converts the world basis and camera-local axes, then compares all 12 camera poses and opening-point projections with the JSON camera path. It does not use Blender's automatic reimport conversion. The actual matrices, numeric front-camera example and errors are in `gltf-coordinate-validation.json`; the cross-format contract is documented explicitly.

## What failed before the release

Initial Blender 5.2 API probes encountered the changed file-output API, and attempting to load a single float multilayer EXR through Blender Image returned no pixels. The released pipeline uses the observed 5.2 API and OpenEXR's `Value.V` channel. All real runs use `--python-exit-code 1` so a Python exception cannot be mistaken for a successful Blender exit.

The first depth assumption was wrong: treating the pass as Euclidean ray range and normalizing it introduced an approximately 1.33 m error in the smoke fixture, causing validation to fail. Direct comparison found the pass already stores camera Z on this runtime; the corrected smoke maximum error was 0.0001774 m. The final 12 views were regenerated separately and verified as above.

## Viewer and limits

The actual offline `file://` viewer was exercised in an isolated Ego Lite space: condition/view/channel switching, expected visible-pixel values, boxes, instance selection, file paths, camera detail keyboard operation and desktop/narrow overflow. Actual screenshots were visually inspected. Narrow layout is browser emulation, not physical-phone acceptance.

This verifies the small resource's internal geometric/data consistency. It does not evaluate a model, real-world generalization, realistic material statistics, glass transmission, architecture standards, engineering BIM, arbitrary edited scenes, enormous datasets, macOS/Linux or third-party GLB importers.

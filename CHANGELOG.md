# Release notes

## v0.1.0 · 2026-11-11

First complete architectural CV fixture release.

- One original low-rise facade with 8 windows and 1 door; clean, balcony and foreground-screen conditions; four fixed perspective cameras, 12 real 960×720 Cycles CPU renders.
- Editable `.blend`, reimport-checked `.glb`, original float EXR passes, numeric semantic/instance PNGs, camera-Z NPY, visible areas/boxes, OpenCV intrinsics and extrinsics.
- Offline viewer for condition/view/channel switches, visible door/window boxes and actual per-instance areas; native files and JSON remain directly available.
- Geometry checks across 4,894 interior rays, projection/depth comparisons and three rejected negative controls. Three source files were reopened and three GLBs imported with mesh/ID/pose checks.
- MIT for all original code, geometry and outputs. No third-party models, textures, customer drawings or tool binaries bundled.

Download `facadeprobe-0.1.0-resource.zip`, unpack and open `data/index.html`. Use Blender 5.2 for editable sources. Regeneration needs the Python requirements and the documented background Blender commands. The ZIP includes source/configuration and the complete ready-made resource.

Known limits: one synthetic building, one lighting setup, opaque window surfaces, controlled geometric occluders, visible-only labels, no model score, benchmark or engineering BIM claim. Tests were on Windows 11 / Blender 5.2; browser narrow emulation does not replace a phone test. GLB importer verification used Blender.

Repository: https://github.com/aevumworks/facadeprobe

Release: https://github.com/aevumworks/facadeprobe/releases/tag/v0.1.0

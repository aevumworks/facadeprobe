"""Reopen every .blend and independently reimport every .glb in background Blender."""

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def snapshot():
    meshes=[obj for obj in bpy.context.scene.objects if obj.type=="MESH"]
    by_instance={}
    for obj in meshes:
        if "instance_id" not in obj or "category_id" not in obj:
            raise ValueError(f"Missing semantic metadata on {obj.name}")
        key=int(obj["instance_id"])
        entry=by_instance.setdefault(key,{"category_id":int(obj["category_id"]),"mesh_count":0,"corners":[]})
        if entry["category_id"]!=int(obj["category_id"]):
            raise ValueError("Inconsistent class within an instance.")
        entry["mesh_count"]+=1
        entry["corners"].extend([list(obj.matrix_world@Vector(corner)) for corner in obj.bound_box])
    for entry in by_instance.values():
        corners=entry.pop("corners")
        entry["min"]=[min(point[axis] for point in corners) for axis in range(3)]
        entry["max"]=[max(point[axis] for point in corners) for axis in range(3)]
    cameras={obj.name:[list(row) for row in obj.matrix_world] for obj in bpy.context.scene.objects if obj.type=="CAMERA"}
    return {"mesh_count":len(meshes),"instances":by_instance,"camera_count":len(cameras),"camera_poses":cameras}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:]);root=args.root.resolve()
    manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    results=[]
    for case in manifest["cases"]:
        bpy.ops.wm.open_mainfile(filepath=str(root/case["blend"]))
        bpy.context.view_layer.update();native=snapshot()
        assert native["mesh_count"]==case["mesh_object_count"]
        assert native["camera_count"]==4
        # Relative paths make the editable source portable after unpacking.
        assert bpy.context.scene.render.filepath.startswith("//")
        assert all(node.directory.startswith("//") for node in bpy.context.scene.compositing_node_group.nodes if node.bl_idname=="CompositorNodeOutputFile")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(root/case["glb"]))
        bpy.context.view_layer.update();imported=snapshot()
        assert imported["mesh_count"]==native["mesh_count"]
        assert imported["camera_count"]==native["camera_count"]
        assert set(imported["camera_poses"])==set(native["camera_poses"])
        pose_error=max(abs(a-b) for name,original in native["camera_poses"].items() for row,other in zip(original,imported["camera_poses"][name]) for a,b in zip(row,other))
        assert pose_error<0.00001
        assert set(imported["instances"])==set(native["instances"])
        error=0.0
        for key,original in native["instances"].items():
            other=imported["instances"][key]
            assert original["category_id"]==other["category_id"]
            assert original["mesh_count"]==other["mesh_count"]
            error=max(error,max(abs(a-b) for bound in ("min","max") for a,b in zip(original[bound],other[bound])))
        # Beveled evaluated export can shrink an AABB by a few millimetres.
        assert error<0.005,(case["name"],error)
        results.append({"case":case["name"],"blend_reopened":True,"glb_reimported":True,"mesh_count":native["mesh_count"],"camera_count":native["camera_count"],"semantic_instance_count":len(native["instances"]),"max_world_aabb_difference_m":error,"max_camera_pose_difference":pose_error,"relative_render_paths":True,"passed":True})
        print("IMPORT_CHECK_PASSED",case["name"],flush=True)
    (root/"import-validation.json").write_text(json.dumps({"passed":True,"blender":bpy.app.version_string,"cases":results},indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()

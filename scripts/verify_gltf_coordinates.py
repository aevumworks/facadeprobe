"""Check native GLB camera transforms without Blender's automatic Y/Z conversion."""

import argparse
import json
from pathlib import Path
import struct

import numpy as np


def glb_json(path):
    raw=path.read_bytes()
    magic,version,length=struct.unpack_from("<4sII",raw,0)
    if magic!=b"glTF" or version!=2 or length!=len(raw):
        raise ValueError("Expected a complete glTF 2.0 binary.")
    size,kind=struct.unpack_from("<II",raw,12)
    if kind!=0x4e4f534a:
        raise ValueError("GLB JSON chunk is missing.")
    return json.loads(raw[20:20+size].decode("utf-8"))


def local_matrix(node):
    if "matrix" in node:
        return np.asarray(node["matrix"],dtype=np.float64).reshape(4,4,order="F")
    x,y,z,w=node.get("rotation",[0,0,0,1])
    result=np.eye(4)
    result[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                  [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                  [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    result[:3,:3]@=np.diag(node.get("scale",[1,1,1]))
    result[:3,3]=node.get("translation",[0,0,0])
    return result


def run(root):
    manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    contract=manifest["model_coordinates"]
    gltf_from_dataset=np.asarray(contract["gltf_from_dataset"],dtype=np.float64)
    dataset_from_gltf=np.asarray(contract["dataset_from_gltf"],dtype=np.float64)
    cv_from_local=np.asarray(contract["opencv_from_gltf_camera_local"],dtype=np.float64)
    assert np.array_equal(gltf_from_dataset@dataset_from_gltf,np.eye(4))
    results=[]
    for case in manifest["cases"]:
        doc=glb_json(root/case["glb"]);nodes=doc["nodes"]
        parents={child:index for index,node in enumerate(nodes) for child in node.get("children",[])}
        def world(index):
            matrix=local_matrix(nodes[index])
            return world(parents[index])@matrix if index in parents else matrix
        for record in manifest["views"]:
            if record["case"]!=case["name"]:
                continue
            index=next(i for i,node in enumerate(nodes) if node.get("name")=="Camera "+record["view"] and "camera" in node)
            native=world(index)
            camera=json.loads((root/record["path"]/"camera.json").read_text(encoding="utf-8"))
            expected_c2w=np.asarray(camera["camera_to_world_cv"])
            converted=dataset_from_gltf@native@cv_from_local
            pose_error=float(np.max(np.abs(converted-expected_c2w)))
            if pose_error>0.00001:
                raise ValueError(f"Native GLB camera disagrees after basis conversion: {pose_error}")
            points=np.asarray([[*point,1] for opening in case["openings"] for point in opening["reference_quad_world"]])
            points_gltf=(gltf_from_dataset@points.T)
            cv_from_native=cv_from_local@np.linalg.inv(native)@points_gltf
            cv_from_json=np.asarray(camera["world_to_camera_cv"])@points.T
            k=np.asarray(camera["K"])
            native_h=k@cv_from_native[:3];json_h=k@cv_from_json[:3]
            uv_native=native_h[:2]/native_h[2];uv_json=json_h[:2]/json_h[2]
            projection_error=float(np.max(np.abs(uv_native-uv_json)))
            if projection_error>0.001:
                raise ValueError("Native GLB / JSON projection mismatch.")
            target=np.asarray([*manifest["fixture"]["camera_target_m"],1.0])
            target_cv=np.asarray(camera["world_to_camera_cv"])@target
            target_h=k@target_cv[:3]
            results.append({"case":case["name"],"view":record["view"],"gltf_camera_world_position":native[:3,3].tolist(),"dataset_camera_world_position":expected_c2w[:3,3].tolist(),"pose_max_abs_difference":pose_error,"projection_max_abs_px":projection_error,"target_dataset_world":target[:3].tolist(),"target_gltf_world":(gltf_from_dataset@target)[:3].tolist(),"target_uv":(target_h[:2]/target_h[2]).tolist(),"passed":True})
    output={"passed":True,"method":"parse native GLB JSON node TRS/matrices; no Blender reimport conversion","coordinates":contract,"camera_checks":results,"max_pose_difference":max(x["pose_max_abs_difference"] for x in results),"max_projection_error_px":max(x["projection_max_abs_px"] for x in results)}
    (root/"gltf-coordinate-validation.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"passed":True,"cameras":len(results),"max_pose_difference":output["max_pose_difference"],"max_projection_error_px":output["max_projection_error_px"],"front_example":results[0]},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path)
    run(parser.parse_args().root.resolve())

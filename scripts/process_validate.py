"""Decode real Cycles passes, export labels, and check them against scene rays."""

import argparse
import json
from pathlib import Path
import math

import numpy as np
from PIL import Image
import OpenEXR


def json_file(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def pass_values(path):
    with OpenEXR.File(str(path)) as source:
        channels=source.channels()
        if set(channels)!={"Value.V"}:
            raise ValueError(f"Unexpected pass channels: {path.name}: {list(channels)}")
        return channels["Value.V"].pixels.copy()


def project(camera,points):
    points=np.asarray(points,dtype=np.float64)
    hom=np.concatenate((points,np.ones((len(points),1))),axis=1)
    cv=hom@np.asarray(camera["world_to_camera_cv"],dtype=np.float64).T
    if np.any(cv[:,2]<=0):
        raise ValueError("A reference point is behind the camera.")
    pixels=cv[:,:3]@np.asarray(camera["K"],dtype=np.float64).T
    return pixels[:,:2]/pixels[:,2,None]


def check_view(camera,semantic,instance,depth,references,mapping):
    shape=(camera["height"],camera["width"])
    if semantic.shape!=shape or instance.shape!=shape or depth.shape!=shape:
        raise ValueError("RGB/label/depth dimensions differ from the camera.")
    allowed=set(map(int,mapping))
    if not set(np.unique(instance)).issubset(allowed):
        raise ValueError("Instance image contains undeclared IDs.")
    lookup=np.zeros(max(allowed)+1,dtype=np.uint8)
    for key,value in mapping.items():
        lookup[int(key)]=value["category_id"]
    if not np.array_equal(lookup[instance],semantic):
        raise ValueError("Semantic and instance IDs disagree.")
    if not np.all(np.isnan(depth[instance==0])) or not np.all(np.isfinite(depth[instance!=0])):
        raise ValueError("Depth background/foreground validity is inconsistent.")
    pairs=references["projection_references"]
    projected=project(camera,[x["world"] for x in pairs])
    expected=np.asarray([x["blender_uv"] for x in pairs])
    projection_error=float(np.max(np.abs(projected-expected)))
    if projection_error>0.001:
        raise ValueError(f"Camera projection error {projection_error:.6f} px exceeds 0.001 px.")
    checked=0;mismatches=[];depth_errors=[]
    for item in references["ray_references"]:
        x,y=item["x"],item["y"]
        patch=instance[max(0,y-2):y+3,max(0,x-2):x+3]
        # Index/Depth passes use a single render sample; avoid subpixel edges.
        if not np.all(patch==instance[y,x]):
            continue
        checked+=1
        if int(instance[y,x])!=item["instance_id"] or int(semantic[y,x])!=item["category_id"]:
            mismatches.append([x,y,int(instance[y,x]),item["instance_id"]])
        if item["category_id"] in (1,2,3,7) and instance[y,x]==item["instance_id"]:
            depth_errors.append(abs(float(depth[y,x])-item["depth_z_m"]))
    if checked<50 or mismatches:
        raise ValueError(f"Independent ray labels disagree: checked={checked}, mismatches={mismatches[:5]}")
    if len(depth_errors)<20:
        raise ValueError("Too few interior building samples for depth validation.")
    depth_max=max(depth_errors)
    if depth_max>0.03:
        raise ValueError(f"Camera-Z depth error {depth_max:.6f} m exceeds 0.03 m.")
    return {"projection_max_abs_px":projection_error,"ray_samples_checked":checked,"ray_label_mismatches":0,"interior_depth_samples":len(depth_errors),"depth_max_abs_m":depth_max,"depth_median_abs_m":float(np.median(depth_errors)),"depth_tolerance_m":0.03}


def negative_controls(camera,semantic,instance,depth,references,mapping):
    altered=json.loads(json.dumps(camera));altered["K"][0][2]+=12
    variants=[("principal_point_shift_12px",altered,semantic,instance,depth),
              ("vertical_flip_of_labels_and_depth",camera,semantic[::-1].copy(),instance[::-1].copy(),depth[::-1].copy()),
              ("depth_scaled_by_1000",camera,semantic,instance,depth*1000)]
    results=[]
    for name,cam,sem,inst,z in variants:
        try:
            check_view(cam,sem,inst,z,references,mapping)
        except ValueError as error:
            results.append({"name":name,"rejected":True,"reason":str(error)})
        else:
            raise ValueError(f"Negative control was incorrectly accepted: {name}")
    return results


def process(root):
    manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    classes=manifest["fixture"]["classes"]
    palette=np.asarray([x["color"] for x in classes],dtype=np.uint8)
    cases={x["name"]:x for x in manifest["cases"]}
    validation=[];first=True
    for record in manifest["views"]:
        folder=root/record["path"]
        camera=json.loads((folder/"camera.json").read_text(encoding="utf-8"))
        references=json.loads((folder/"geometry-checks.json").read_text(encoding="utf-8"))
        raw_instance=pass_values(folder/"raw-instance/instance.exr")
        if not np.all(np.isfinite(raw_instance)) or np.max(np.abs(raw_instance-np.rint(raw_instance)))>1e-5:
            raise ValueError("Object Index pass contains non-integer values.")
        instance=np.rint(raw_instance).astype(np.uint16)
        mapping=cases[record["case"]]["instance_mapping"]
        if not set(np.unique(instance)).issubset(set(map(int,mapping))):
            raise ValueError("Object Index pass contains unknown objects.")
        lookup=np.zeros(max(map(int,mapping))+1,dtype=np.uint8)
        for key,value in mapping.items():
            lookup[int(key)]=value["category_id"]
        semantic=lookup[instance]
        raw_depth=pass_values(folder/"raw-depth/depth.exr")
        height,width=instance.shape
        # Verified on Blender 5.2: this pass already stores camera-Z, not ray range.
        depth=raw_depth.astype(np.float32);depth[instance==0]=np.nan
        rgb=np.asarray(Image.open(folder/"rgb.png").convert("RGB"))
        if rgb.shape[:2]!=(height,width):
            raise ValueError("RGB dimensions disagree with the label pass.")
        metrics=check_view(camera,semantic,instance,depth,references,mapping)
        controls=negative_controls(camera,semantic,instance,depth,references,mapping) if first else []
        first=False
        Image.fromarray(instance).save(folder/"instance.png")
        Image.fromarray(semantic).save(folder/"semantic.png")
        Image.fromarray(palette[semantic]).save(folder/"semantic-color.png")
        overlay=rgb.copy()
        foreground=semantic!=0
        overlay[foreground]=np.rint(rgb[foreground]*.55+palette[semantic[foreground]]*.45).astype(np.uint8)
        Image.fromarray(overlay).save(folder/"overlay.png")
        np.save(folder/"depth-z.npy",depth,allow_pickle=False)
        normalized=np.clip(np.nan_to_num(depth,nan=35)/35,0,1)
        depth_color=np.stack((255*(1-normalized),190*(1-abs(2*normalized-1)),255*normalized),axis=-1).astype(np.uint8)
        depth_color[instance==0]=[235,241,246]
        Image.fromarray(depth_color).save(folder/"depth-preview.png")
        annotations=[]
        for key,value in mapping.items():
            inst=int(key)
            if not inst:
                continue
            y,x=np.nonzero(instance==inst)
            bbox=[int(x.min()),int(y.min()),int(x.max()-x.min()+1),int(y.max()-y.min()+1)] if len(x) else None
            annotations.append({"instance_id":inst,"category_id":value["category_id"],"visible_pixels":len(x),"visible_bbox_xywh":bbox,"visible":bool(len(x))})
        json_file(folder/"annotations.json",{"schema":"facadeprobe.visible.v1","bbox_convention":"integer [x,y,width,height], visible pixels only; null for invisible","instances":annotations})
        # Read back actual encoded label PNGs, including 16-bit instance values.
        if not np.array_equal(np.asarray(Image.open(folder/"instance.png")),instance) or not np.array_equal(np.asarray(Image.open(folder/"semantic.png")),semantic):
            raise ValueError("PNG label round trip changed IDs.")
        for ann in annotations:
            mask=instance==ann["instance_id"]
            if int(mask.sum())!=ann["visible_pixels"]:
                raise ValueError("Visible instance area mismatch.")
            if ann["visible_bbox_xywh"]:
                x,y,w,h=ann["visible_bbox_xywh"]
                if np.count_nonzero(mask[y:y+h,x:x+w])!=ann["visible_pixels"]:
                    raise ValueError("Visible bounding box fails to contain its mask.")
        validation.append({"case":record["case"],"view":record["view"],"passed":True,**metrics,"negative_controls":controls})
        print("VALIDATED",record["case"],record["view"],json.dumps(metrics),flush=True)
    pairs=[]
    if "clean" in cases:
        for record in manifest["views"]:
            if record["case"]=="clean":
                continue
            before=root/"views/clean"/record["view"]/"annotations.json"
            if not before.exists():
                continue
            left=json.loads(before.read_text(encoding="utf-8"))["instances"]
            right=json.loads((root/record["path"]/"annotations.json").read_text(encoding="utf-8"))["instances"]
            old={x["instance_id"]:x for x in left if x["category_id"] in (2,3)}
            current={x["instance_id"]:x for x in right if x["category_id"] in (2,3)}
            for inst,original in old.items():
                value=current[inst]
                if value["visible_pixels"]>original["visible_pixels"]:
                    raise ValueError("Added occluders unexpectedly increased a window/door's visible area.")
                pairs.append({"case":record["case"],"view":record["view"],"instance_id":inst,"clean_visible_pixels":original["visible_pixels"],"occluded_visible_pixels":value["visible_pixels"],"hidden_fraction_of_clean_visible_pixels":1-value["visible_pixels"]/original["visible_pixels"] if original["visible_pixels"] else None})
    result={"schema":"facadeprobe.validation.v1","passed":True,"view_count":len(validation),"views":validation,"paired_visibility":pairs,"depth_definition":"float32 camera-Z metres from the verified Blender 5.2 Cycles Depth pass; NaN for background.","not_validated":["real-world domain generalization","model training accuracy","professional BIM semantics","physical glass transmission","macOS/Linux runtime"]}
    json_file(root/"validation.json",result)
    json_file(root/"classes.json",classes)
    print("RESOURCE_VALIDATION_PASSED",len(validation),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path)
    process(parser.parse_args().root.resolve())

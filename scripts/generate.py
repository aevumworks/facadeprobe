"""Run with Blender 5.2 in a new background process, never the live user scene."""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def material(name, color, roughness=0.7, metallic=0.0):
    value=bpy.data.materials.new(name)
    value.diffuse_color=(*color,1)
    value.use_nodes=True
    shader=value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value=(*color,1)
    shader.inputs["Roughness"].default_value=roughness
    shader.inputs["Metallic"].default_value=metallic
    return value


def box(name, center, dimensions, mat, category, instance, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    obj=bpy.context.object;obj.name=name;obj.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(mat)
    obj.pass_index=instance;obj["category_id"]=category;obj["instance_id"]=instance
    if bevel:
        modifier=obj.modifiers.new("Edge finish","BEVEL");modifier.width=bevel;modifier.segments=2
    return obj


def build_geometry(config, case):
    wall=material("Limestone",(.67,.63,.54))
    trim=material("Pale mineral trim",(.83,.81,.74))
    frame=material("Powder coated frame",(.08,.15,.18),.38,.35)
    glazing=material("Opaque blue window surface",(.055,.15,.22),.23,.25)
    door=material("Timber door",(.27,.14,.075),.55)
    metal=material("Balcony steel",(.20,.28,.32),.35,.55)
    ground=material("Concrete",(.46,.49,.48))
    screen=material("Terracotta screen",(.45,.16,.10))
    roof=material("Roof edge",(.24,.28,.30))
    w,h,d=config["width_m"],config["height_m"],config["depth_m"]
    openings=[];number=100
    for level,z in enumerate(config["levels_z_m"]):
        for column,x in enumerate(config["columns_x_m"]):
            is_door=level==0 and column==1
            if is_door:
                ww,hh,zz,category,instance=1.5,2.4,1.2,3,201
            else:
                number+=1
                ww,hh,zz,category,instance=config["window_width_m"],config["window_height_m"],z,2,number
            openings.append({"instance_id":instance,"category_id":category,"x":x,"z":zz,"width":ww,"height":hh})
    xs=sorted(set([-w/2,w/2]+[edge for op in openings for edge in (op["x"]-op["width"]/2,op["x"]+op["width"]/2)]))
    zs=sorted(set([0,h]+[edge for op in openings for edge in (op["z"]-op["height"]/2,op["z"]+op["height"]/2)]))
    for ix,(x0,x1) in enumerate(zip(xs,xs[1:])):
        for iz,(z0,z1) in enumerate(zip(zs,zs[1:])):
            x,z=(x0+x1)/2,(z0+z1)/2
            inside=any(abs(x-op["x"])<op["width"]/2 and abs(z-op["z"])<op["height"]/2 for op in openings)
            if not inside:
                box(f"Front wall {ix}-{iz}",(x,.175,z),(x1-x0,.35,z1-z0),wall,1,1)
    # Returns start behind the front wall to avoid overlapping coplanar faces.
    box("Left return",(-w/2+.16,(d+.35)/2,h/2),(.32,d-.35,h),wall,1,1)
    box("Right return",(w/2-.16,(d+.35)/2,h/2),(.32,d-.35,h),wall,1,1)
    box("Back wall",(0,d-.16,h/2),(w,.32,h),wall,1,1)
    box("Roof slab",(0,d/2,h+.04),(w+.18,d+.18,.20),roof,7,7,.02)
    for x in (-w/2,w/2):
        box("Parapet side",(x,d/2,h+.32),(.16,d,.42),trim,7,7,.015)
    for y in (0,d):
        box("Parapet edge",(0,y,h+.32),(w,.16,.42),trim,7,7,.015)
    box("Ground",(0,-1,-.14),(32,30,.26),ground,6,6,.02)
    for op in openings:
        x,z,ww,hh=op["x"],op["z"],op["width"],op["height"]
        cat,inst=op["category_id"],op["instance_id"]
        name=f"{'Window' if cat==2 else 'Door'} {inst}"
        box(name+" inset surface",(x,.27,z),(ww-.12,.06,hh-.12),glazing if cat==2 else door,cat,inst,.008)
        for sign in (-1,1):
            box(name+" jamb",(x+sign*(ww/2-.035),.10,z),(.07,.32,hh),frame,cat,inst,.008)
            box(name+" rail",(x,.10,z+sign*(hh/2-.035)),(ww,.32,.07),frame,cat,inst,.008)
        box(name+" mullion",(x,.12,z),(.045,.30,hh-.1),frame,cat,inst,.006)
        if cat==2:
            box(name+" transom",(x,.13,z+.15),(ww-.1,.28,.04),frame,cat,inst,.005)
            box(name+" sill",(x,-.13,z-hh/2-.045),(ww+.22,.45,.09),trim,1,1,.012)
        else:
            box(name+" handle",(x+.24,-.095,z),(.035,.035,.30),metal,cat,inst,.01)
        op["reference_quad_world"]=[[x-ww/2,-.065,z-hh/2],[x+ww/2,-.065,z-hh/2],[x+ww/2,-.065,z+hh/2],[x-ww/2,-.065,z+hh/2]]
    for z in (3.1,5.9):
        box("Floor band",(0,-.035,z),(w+.04,.18,.10),trim,1,1,.01)
    if case=="balcony":
        for level,z in enumerate((3.46,6.26),1):
            instance=400+level
            box(f"Balcony {level} slab",(0,-.88,z),(10.8,1.9,.20),trim,4,instance,.025)
            for offset in (.35,.70,1.06):
                box(f"Balcony {level} horizontal rail",(0,-1.80,z+offset),(10.7,.055,.055),metal,4,instance,.01)
            for index in range(21):
                box(f"Balcony {level} post {index}",(-5.25+index*.525,-1.80,z+.58),(.04,.04,1.06),metal,4,instance,.006)
            for x in (-5.28,5.28):
                box(f"Balcony {level} side rail",(x,-.90,z+1.06),(.055,1.8,.055),metal,4,instance,.008)
    if case=="screen":
        for index in range(16):
            box(f"Screen slat {index}",(-.2+index*.30,-3.1,2.65),(.14,.14,5.3),screen,5,501,.018)
        for z in (.12,5.18):
            box("Screen crossbar",(2.05,-3.1,z),(4.8,.18,.12),metal,5,501,.01)
        box("Foreground opaque panel",(-3.7,-2.0,1.60),(2.6,.16,2.65),screen,5,502,.025)
    return openings


def setup(config, case, args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.engine="CYCLES";scene.cycles.device="CPU";scene.cycles.samples=args.samples
    scene.cycles.use_denoising=True
    scene.render.threads_mode="FIXED";scene.render.threads=args.threads
    scene.render.resolution_x=args.width;scene.render.resolution_y=args.height;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGB";scene.render.image_settings.color_depth="8"
    scene.render.film_transparent=False
    scene.view_settings.view_transform="AgX"
    world=bpy.data.worlds.new("Studio sky");world.use_nodes=True;scene.world=world
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(.61,.72,.85,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=.38
    light_data=bpy.data.lights.new("Large daylight","AREA");light_data.energy=2000;light_data.shape="DISK";light_data.size=8
    light=bpy.data.objects.new("Large daylight",light_data);scene.collection.objects.link(light);light.location=(-5,-7,13)
    light.rotation_euler=(Vector((0,0,4))-light.location).to_track_quat("-Z","Y").to_euler()
    openings=build_geometry(config,case)
    cameras={}
    for name,position in config["cameras"].items():
        data=bpy.data.cameras.new(name);data.lens=40;data.sensor_width=36;data.sensor_fit="HORIZONTAL";data.clip_start=.1;data.clip_end=100
        camera=bpy.data.objects.new("Camera "+name,data);scene.collection.objects.link(camera);camera.location=position
        camera.rotation_euler=(Vector(config["camera_target_m"])-camera.location).to_track_quat("-Z","Y").to_euler()
        cameras[name]=camera
    layer=scene.view_layers[0];layer.use_pass_object_index=True;layer.use_pass_z=True
    tree=bpy.data.node_groups.new("FacadeProbe raw geometry passes","CompositorNodeTree");scene.compositing_node_group=tree
    source=tree.nodes.new("CompositorNodeRLayers")
    nodes={}
    for name,socket in (("instance","Object Index"),("depth","Depth")):
        node=tree.nodes.new("CompositorNodeOutputFile");node.name=name
        node.file_output_items.new("FLOAT","Value")
        node.file_name=name;node.format.file_format="OPEN_EXR_MULTILAYER";node.format.color_depth="32"
        tree.links.new(source.outputs[socket],node.inputs[0]);nodes[name]=node
    scene["facadeprobe_version"]="0.1.0";scene["case"]=case
    return scene,cameras,nodes,openings


def camera_metadata(scene,camera,openings):
    width,height=scene.render.resolution_x,scene.render.resolution_y
    focal=width*camera.data.lens/camera.data.sensor_width
    K=[[focal,0,width/2],[0,focal,height/2],[0,0,1]]
    conversion=Matrix(((1,0,0),(0,-1,0),(0,0,-1)))
    world_to_blender=camera.matrix_world.inverted()
    rotation=conversion@world_to_blender.to_3x3();translation=conversion@world_to_blender.translation
    transform=rotation.to_4x4();transform.translation=translation
    projection=[]
    for op in openings:
        for world in op["reference_quad_world"]:
            cv=rotation@Vector(world)+translation
            software=[focal*cv.x/cv.z+width/2,focal*cv.y/cv.z+height/2]
            native=world_to_camera_view(scene,camera,Vector(world))
            reference=[native.x*width,(1-native.y)*height]
            projection.append({"world":world,"opencv_uv":software,"blender_uv":reference})
    samples=[];origin=camera.matrix_world.translation;cam_rotation=camera.matrix_world.to_3x3()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    step=max(8,min(width,height)//18)
    for y in range(step//2,height,step):
        for x in range(step//2,width,step):
            u,v=x+.5,y+.5
            direction=(cam_rotation@Vector(((u-width/2)/focal,-(v-height/2)/focal,-1))).normalized()
            hit,location,normal,index,obj,matrix=scene.ray_cast(depsgraph,origin,direction,distance=100)
            samples.append({"x":x,"y":y,"instance_id":int(obj["instance_id"]) if hit else 0,"category_id":int(obj["category_id"]) if hit else 0,"range_m":(location-origin).length if hit else None,"depth_z_m":(rotation@location+translation).z if hit else None})
    return {"schema":"facadeprobe.camera.v1","width":width,"height":height,"K":K,"world_to_camera_cv":[list(row) for row in transform],"camera_to_world_cv":[list(row) for row in transform.inverted()],"pixel_convention":"u right, v down; image upper-left corner is (0,0); pixel (x,y) center is (x+0.5,y+0.5)","world_convention":"right-handed metres; X right along facade, Z up, front-facing direction is -Y","camera_convention":"OpenCV: X right, Y down, Z forward","distortion":[0,0,0,0,0]}, {"projection_references":projection,"ray_references":samples}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--width",type=int,default=960);parser.add_argument("--height",type=int,default=720)
    parser.add_argument("--samples",type=int,default=12);parser.add_argument("--threads",type=int,default=4)
    parser.add_argument("--cases",nargs="+",choices=("clean","balcony","screen"),default=["clean","balcony","screen"])
    parser.add_argument("--views",nargs="+",choices=("front","left","right","high"),default=["front","left","right","high"])
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    if min(args.width,args.height,args.samples,args.threads)<=0:
        parser.error("Width, height, samples and threads must be positive.")
    if bpy.app.version[:2]!=(5,2):
        parser.error("This release is verified against Blender 5.2; use that version.")
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    (output/"scenes").mkdir()
    config=json.loads((ROOT/"configs/fixture.json").read_text(encoding="utf-8"))
    manifest={"schema":"facadeprobe.resource.v1","version":"0.1.0","fixture":config,"model_coordinates":config["model_coordinates"],"blender":bpy.app.version_string,"render":{"engine":"Cycles","device":"CPU","samples":args.samples,"width":args.width,"height":args.height,"denoising":True},"depth_raw":"Blender 5.2 Cycles Depth pass: camera-Z metres, background 1e10; independently checked against ray-hit positions transformed into the OpenCV camera","views":[],"cases":[]}
    for case in args.cases:
        scene,cameras,nodes,openings=setup(config,case,args)
        bpy.context.view_layer.update()
        mapping={0:{"category_id":0,"objects":[]}}
        for obj in scene.objects:
            if obj.type=="MESH":
                inst=int(obj["instance_id"]);entry=mapping.setdefault(inst,{"category_id":int(obj["category_id"]),"objects":[]})
                entry["objects"].append(obj.name)
        for view in args.views:
            camera=cameras[view];scene.camera=camera;bpy.context.view_layer.update()
            folder=output/"views"/case/view;folder.mkdir(parents=True)
            for name,node in nodes.items():
                node.directory=str(folder/("raw-"+name))
            scene.render.filepath=str(folder/"rgb.png")
            bpy.ops.render.render(write_still=True)
            metadata,references=camera_metadata(scene,camera,openings)
            write_json(folder/"camera.json",metadata);write_json(folder/"geometry-checks.json",references)
            manifest["views"].append({"case":case,"view":view,"path":f"views/{case}/{view}"})
            print("FACADEPROBE_VIEW_DONE",case,view,flush=True)
        first=args.views[0];scene.camera=cameras[first]
        scene.render.filepath=f"//../views/{case}/{first}/rgb.png"
        for name,node in nodes.items():
            node.directory=f"//../views/{case}/{first}/raw-{name}"
        blend=output/"scenes"/(case+".blend")
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        bpy.ops.export_scene.gltf(filepath=str(output/"scenes"/(case+".glb")),export_format="GLB",export_extras=True,export_cameras=True,export_yup=True)
        manifest["cases"].append({"name":case,"blend":f"scenes/{case}.blend","glb":f"scenes/{case}.glb","instance_mapping":mapping,"openings":openings,"mesh_object_count":sum(obj.type=="MESH" for obj in scene.objects)})
    write_json(output/"manifest.json",manifest)
    print("FACADEPROBE_GENERATION_COMPLETE",len(manifest["views"]),flush=True)


if __name__=="__main__":
    main()

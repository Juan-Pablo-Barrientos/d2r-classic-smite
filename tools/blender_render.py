# Render an animated glTF to a contact sheet (Workbench, headless).
# blender -b --factory-startup -P blender_render.py -- <in.gltf> <out.png> <frames comma list|"views"> [azimuth_deg] [elev_deg]
import math
import sys
import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, dst, frames_arg = args[0], args[1], args[2]
azimuth = float(args[3]) if len(args) > 3 else 0.0
elev = float(args[4]) if len(args) > 4 else 35.0

if src.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=src)  # e.g. make_smite.py's saved scene, body meshes included
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
if not src.endswith(".blend"):
    bpy.ops.import_scene.gltf(filepath=src)
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.lower().startswith("icosphere"):
        o.hide_render = True  # LSLib's placeholder
    if frames_arg == "rest" and o.type == "ARMATURE":
        o.animation_data_clear()
        for pb in o.pose.bones:
            pb.matrix_basis.identity()
if frames_arg == "rest":
    frames_arg = "views"

# stand-ins for the item models: a shield on shield_attach, a sword on R_weapon_attach
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")


def attach(obj, bone, color):
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    obj.matrix_parent_inverse.identity()
    m = bpy.data.materials.new(bone)
    m.diffuse_color = color
    obj.data.materials.append(m)


bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0)
shield = bpy.context.active_object
shield.scale = (0.9, 0.12, 1.15)
attach(shield, "shield_attach", (0.35, 0.45, 0.8, 1))
bpy.ops.mesh.primitive_cube_add(size=1.0)
sword = bpy.context.active_object
sword.scale = (0.08, 3.0, 0.2)
sword.location = (0, 1.5, 0)
attach(sword, "R_weapon_attach", (0.85, 0.3, 0.25, 1))
scene.display.shading.color_type = "MATERIAL"
for o in bpy.data.objects:
    if o.type == "MESH" and o not in (shield, sword):
        if not o.data.materials:
            o.data.materials.append(bpy.data.materials.new("body"))
        for mat in o.data.materials:
            if mat:
                mat.diffuse_color = (0.75, 0.68, 0.55, 1)

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.75, 0.68, 0.55)
scene.display.shading.show_cavity = True
scene.render.resolution_x = scene.render.resolution_y = 320
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.15, 0.15, 0.18)

meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and o not in (shield, sword)]
scene.frame_set(0)
dg = bpy.context.evaluated_depsgraph_get()
pts = [o.evaluated_get(dg).matrix_world @ Vector(c) for o in meshes for c in o.evaluated_get(dg).bound_box]
center = sum(pts, Vector()) / len(pts)
size = max((p - center).length for p in pts)
# ground floor marker so stance/crouch reads clearly
bpy.ops.mesh.primitive_plane_add(size=size * 3, location=(center.x, center.y, min(p.z for p in pts)))
floor = bpy.context.active_object
mat = bpy.data.materials.new("floor"); floor.data.materials.append(mat)

cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"; cam_data.ortho_scale = size * 2.3
cam = bpy.data.objects.new("cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam


def place(az):
    a, e = math.radians(az), math.radians(elev)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * size * 4
    cam.location = center + d
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()


shots = []
if frames_arg == "views":
    for az in (0, 90, 180, 270):
        shots.append((0, az))
else:
    for f in frames_arg.split(","):
        shots.append((int(f), azimuth))

tiles = []
for f, az in shots:
    scene.frame_set(f)
    place(az)
    scene.render.filepath = dst + f".tmp_{len(tiles)}.png"
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(scene.render.filepath)
    a = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    tiles.append(a)
    bpy.data.images.remove(img)

cols = int(args[5]) if len(args) > 5 else (6 if len(tiles) > 6 else len(tiles))
rows = math.ceil(len(tiles) / cols)
h, w = tiles[0].shape[:2]
sheet = np.zeros((rows * h, cols * w, 4), dtype=np.float32)
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    sheet[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = t  # Blender images are bottom-up
out = bpy.data.images.new("sheet", cols * w, rows * h, alpha=True)
out.pixels = sheet.ravel()
out.filepath_raw = dst
out.file_format = "PNG"
out.save()
import os
for i in range(len(tiles)):
    os.remove(dst + f".tmp_{i}.png")
print("wrote", dst, "shots", shots)

# Report, per frame, how deep the sword blade and the sword forearm go inside the body.
# The body is approximated by capsules around bone segments (radius in feet); the blade is the
# R_weapon_attach +Y axis, 3.3 ft long (the in-game sword reaches ~3 ft past the hand).
# blender -b --factory-startup -P blender_clip_check.py -- <scene.blend>
import sys
import bpy
from mathutils import Vector
from mathutils.geometry import intersect_point_line

bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
pb = arm.pose.bones
sc = bpy.context.scene

BODY = [  # (from bone head, to bone head, radius ft, label)
    ("pelvis_bind_jnt", "spine_02_bind_jnt", 0.55, "hips"),
    ("spine_02_bind_jnt", "spine_04_bind_jnt", 0.6, "torso"),
    ("spine_04_bind_jnt", "neck_bind_jnt", 0.5, "chest"),
    ("neck_bind_jnt", "head", 0.4, "head"),
    ("L_leg_01_bind_jnt", "L_leg_02_bind_jnt", 0.35, "L thigh"),
    ("L_leg_02_bind_jnt", "L_leg_03_bind_jnt", 0.27, "L shin"),
    ("R_leg_01_bind_jnt", "R_leg_02_bind_jnt", 0.35, "R thigh"),
    ("R_leg_02_bind_jnt", "R_leg_03_bind_jnt", 0.27, "R shin"),
]
BLADE_LEN = 3.3


def seg_point_depth(p, a, b, r):
    q, t = intersect_point_line(p, a, b)
    t = max(0.0, min(1.0, t))
    q = a + (b - a) * t
    return r - (p - q).length  # > 0 means inside


def worst(points):
    best = (-9.0, "")
    for p in points:
        for a, b, r, label in BODY:
            d = seg_point_depth(p, pb[a].matrix.translation, pb[b].matrix.translation, r)
            if d > best[0]:
                best = (d, label)
    return best


total = 0.0
for f in range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(f)
    w = pb["R_weapon_attach"].matrix
    base, axis = w.translation, w.col[1].xyz.normalized()
    blade = [base + axis * (BLADE_LEN * i / 12) for i in range(1, 13)]
    elbow, wrist = pb["R_lwr_arm_bind_jnt"].matrix.translation, pb["R_hand_bind_jnt"].matrix.translation
    forearm = [elbow + (wrist - elbow) * (i / 6) for i in range(0, 7)]
    bd, bl = worst(blade)
    fd, fl = worst(forearm)
    flag = "  <-- CLIP" if max(bd, fd) > 0.05 else ""
    total += max(bd, 0) + max(fd, 0)
    print(f"frame {f:2d}: blade {bd:+.2f} ft ({bl:7s})  forearm {fd:+.2f} ft ({fl:7s}){flag}")
print(f"total penetration {total:.2f}")

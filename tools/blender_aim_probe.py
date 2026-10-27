# Compare the original clip's aim_location track with the weapon line and the head, frame by frame.
import sys, bpy
from mathutils import Vector
src = sys.argv[sys.argv.index("--") + 1]
# aim_location knots from the original 1hs_skill1 (Granny x, y-up, z-back), from read_vectors.ps1
T = [0.00, 0.05, 0.09, 0.14, 0.19, 0.23, 0.28, 0.32, 0.37, 0.41, 0.46, 0.51, 0.55, 0.60, 0.64, 0.69, 0.73]
AX = [0.22, -0.80, -1.53, -1.85, -2.51, -2.06, -0.75, -0.95, -0.62, -0.47, -0.27, -0.13, 0.01, 0.11, 0.18, 0.22, 0.22]
AY = [6.51, 4.31, 2.84, 2.53, 0.84, 3.52, 8.03, 6.90, 7.32, 7.01, 6.99, 6.82, 6.70, 6.59, 6.53, 6.51, 6.51]
AZ = [5.62, 6.29, 5.88, 5.98, 5.45, 6.70, 6.51, 6.23, 6.15, 5.94, 5.78, 5.66, 5.63, 5.61, 5.62, 5.62, 5.62]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=src)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE"); pb = arm.pose.bones
def dist_to_line(p, a, d): d = d.normalized(); return ((p - a) - d * (p - a).dot(d)).length, (p - a).dot(d)
for t, x, y, z in zip(T, AX, AY, AZ):
    bpy.context.scene.frame_set(round(t * 30))
    aim = Vector((x, -z, y))  # Granny -> Blender
    w = pb["R_weapon_attach"].matrix; wp = w.translation
    hand = pb["R_hand_bind_jnt"].matrix.translation
    head = pb["head_bind_jnt"].matrix.translation
    best = min(((dist_to_line(aim, wp, w.col[i].xyz * s), "xyz"[i] + ("+" if s > 0 else "-")) for i in range(3) for s in (1, -1)), key=lambda r: (r[0][0] if r[0][1] > 0 else 99))
    print(f"t={t:.2f} aim={tuple(round(c,1) for c in aim)} weapon={tuple(round(c,1) for c in wp)} "
          f"off weapon {best[1]} axis {best[0][0]:.2f} at {best[0][1]:.1f}ft | aim-head dir {tuple(round(c,2) for c in (aim-head).normalized())} | aim-hand {(aim-hand).length:.1f}")

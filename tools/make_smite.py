# Build a classic-D2-style Smite on the HD Paladin skeleton and export it as .glb.
# blender -b --factory-startup -P make_smite.py -- <in.gltf (current Smite, linear)> <out.glb> [out.blend]
#
# World axes after glTF import: the Paladin faces -Y, up is +Z, his left is +X.
# Poses are keyed on the original Smite's 22 frames (30 fps); the hit is at frame 13
# (classic Smite hits on frame 7 of 12).
import json
import math
import sys
import bpy
from mathutils import Matrix, Quaternion, Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, dst = args[0], args[1]
blend_out = args[2] if len(args) > 2 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=src)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
pbs = arm.pose.bones
LAST = 22

# ---------------------------------------------------------------- base pose (frame 0 of the original)
scene.frame_set(0)
base_basis = {pb.name: pb.matrix_basis.copy() for pb in pbs}
base_world = {pb.name: pb.matrix.copy() for pb in pbs}
arm.animation_data.action = bpy.data.actions.new("smite_classic")


def reset_to_base():
    for pb in pbs:
        pb.matrix_basis = base_basis[pb.name]
    bpy.context.view_layer.update()


def set_matrix(name, m):
    pbs[name].matrix = m
    bpy.context.view_layer.update()


def rotate(name, axis, deg):
    """Rotate a bone about a world axis through its head (children follow)."""
    m = pbs[name].matrix.copy()
    pivot = m.translation.copy()
    r = Matrix.Rotation(math.radians(deg), 4, Vector(axis))
    set_matrix(name, Matrix.Translation(pivot) @ r @ Matrix.Translation(-pivot) @ m)


def move_to(name, pos):
    m = pbs[name].matrix.copy()
    m.translation = Vector(pos)
    set_matrix(name, m)


SPINE = ["spine_01_bind_jnt", "spine_02_bind_jnt", "spine_03_bind_jnt", "spine_04_bind_jnt"]


def torso(twist=0.0, bend=0.0, lean=0.0):
    """twist: +Z = left shoulder back; bend: + = forward; lean: + = toward his left. Spread over the spine.
    Bend and lean use the twisted torso's own axes, so a twisted body still bends toward its chest."""
    for s in SPINE:
        if twist:
            rotate(s, (0, 0, 1), twist / len(SPINE))
    turn = Matrix.Rotation(math.radians(twist), 3, "Z")
    for s in SPINE:
        if bend:
            rotate(s, turn @ Vector((1, 0, 0)), bend / len(SPINE))
        if lean:
            rotate(s, turn @ Vector((0, 1, 0)), -lean / len(SPINE))


# ---------------------------------------------------------------- IK rigs
def empty(name, loc):
    e = bpy.data.objects.new(name, None)
    scene.collection.objects.link(e)
    e.location = loc
    return e


def ik(bone, target, chain):
    c = pbs[bone].constraints.new("IK")
    c.target = target
    c.use_tail = False  # bone's head (wrist/ankle) is the effector
    c.chain_count = chain
    c.iterations = 500
    return c


head_of = lambda n: base_world[n].translation.copy()
T = {
    "lfoot": empty("t_lfoot", head_of("L_leg_03_bind_jnt")),
    "rfoot": empty("t_rfoot", head_of("R_leg_03_bind_jnt")),
    "lhand": empty("t_lhand", head_of("L_hand_bind_jnt")),
    "rhand": empty("t_rhand", head_of("R_hand_bind_jnt")),
}
# Limbs have twist bones between the joints: hand <- 2 forearm twists <- forearm <- upper-arm twist <- upper arm
# (legs likewise). A chain of 6 reaches the upper arm/thigh, and with use_tail off it also takes in the bone
# above (collarbone/pelvis), which then tilted the whole torso. Lock those and the twist bones so the solver
# bends only the real joints; the torso and collarbones come from the key poses.
for pb in pbs:
    if "_twist_" in pb.name or pb.name in ("pelvis_bind_jnt", "L_shoulder_bind_jnt", "R_shoulder_bind_jnt"):
        pb.lock_ik_x = pb.lock_ik_y = pb.lock_ik_z = True
IK = {
    "lfoot": ik("L_leg_03_bind_jnt", T["lfoot"], 6),
    "rfoot": ik("R_leg_03_bind_jnt", T["rfoot"], 6),
    "lhand": ik("L_hand_bind_jnt", T["lhand"], 6),
    "rhand": ik("R_hand_bind_jnt", T["rhand"], 6),
}

# ---------------------------------------------------------------- key poses
P0 = head_of("pelvis_bind_jnt")  # (0.17, 0.29, 3.65)
L0 = tuple(head_of("L_leg_03_bind_jnt"))  # left ankle in the ready stance (0.78, -1.11, 0.36); it stays put
R0 = head_of("R_leg_03_bind_jnt")  # right ankle in the ready stance (-0.61, 1.64, 0.47)
R_FWD = (-0.75, -3.3, 0.36)  # right ankle planted ~2.2 ft in front of the left foot
KEYS = {
    0: None,  # original ready stance
    # Footwork from the classic sprites (side and front views): the LEFT foot never moves. The RIGHT (back)
    # foot lifts (2), passes beside the left foot (4) and plants about 2 ft in front of it (8); the body
    # travels ~2.4 ft forward over it and sinks into the crouch for the punch (11-13). On the recovery the
    # right foot steps back past the left foot (18-20) to the ready stance (22).
    # hips: pelvis yaw, + = right hip forward (follows the right foot).
    2: dict(  # classic 1: weight onto the left foot, right foot lifting, shield starting out
        pelvis=(0.2, 0.0, 3.55), hips=5, twist=10,
        lhand=(1.9, -0.4, 4.3), rhand=(-1.1, 0.3, 3.6),
        lfoot=L0, rfoot=(-0.6, 1.0, 0.75)),
    4: dict(  # classic 2: right foot passing beside the left, shield swinging out, sword sweeping low
        pelvis=(0.22, -0.6, 3.45), hips=10, twist=25, bend=2,
        lhand=(2.0, 0.0, 4.8), rhand=(-0.6, -1.0, 3.4),
        lfoot=L0, rfoot=(-0.5, -1.0, 0.95)),
    6: dict(  # classic 3: right foot reaching forward, wind-up building
        pelvis=(0.15, -1.2, 3.3), hips=18, twist=40, bend=2,
        lhand=(1.7, -0.2, 5.2), rhand=(0.3, -2.4, 3.3), sword=(0.5, 0.5, 0.2),
        lfoot=L0, rfoot=(-0.65, -2.4, 0.75)),
    8: dict(  # classic 4: right foot planted in front, shield back by the left shoulder, sword low across
        pelvis=(0.1, -1.7, 3.05), hips=22, twist=45, bend=-3, lean=4,
        lhand=(1.6, -0.5, 5.3), rhand=(0.6, -3.4, 3.2), sword=(0.6, 0.7, 0.4),
        lfoot=L0, rfoot=R_FWD),
    9: dict(  # classic 5: wind-up peak
        pelvis=(0.1, -1.8, 3.0), hips=22, twist=45, bend=-3, lean=4,
        lhand=(1.6, -0.4, 5.3), rhand=(0.7, -3.6, 3.2), sword=(0.6, 0.7, 0.4),
        lfoot=L0, rfoot=R_FWD),
    # The punch comes as the body drives forward and down over the right foot.
    11: dict(  # classic 6: shield arm coming through, nearly straight, sword going up
        pelvis=(0.12, -2.0, 2.7), hips=20, twist=-35, bend=20, lclav=-15,
        lhand=(0.6, -6.4, 3.9), rhand=(-1.1, -1.6, 6.0), sword=(-0.2, 0.55, 0.8),
        lfoot=L0, rfoot=R_FWD),
    12: dict(  # arm locks out while the body is still sinking forward
        pelvis=(0.12, -2.1, 2.55), hips=20, twist=-60, bend=33, lclav=-22,
        lhand=(0.45, -7.8, 3.7), rhand=(-0.95, -2.2, 6.3), sword=(-0.3, 0.7, 0.65),
        lfoot=L0, rfoot=R_FWD),
    13: dict(  # classic 7 (hit): deep crouch over the right foot, shield arm punched out, sword high
        # the hand target sits well past arm's reach so IK locks the arm straight; lclav pushes the
        # shoulder joint forward for extra reach
        pelvis=(0.1, -2.15, 2.45), hips=20, twist=-65, bend=37, lclav=-25,
        lhand=(0.4, -8.2, 3.6), rhand=(-0.9, -2.3, 6.3), sword=(-0.3, 0.7, 0.65),
        lfoot=L0, rfoot=R_FWD),
    17: dict(  # classic 9: holding the crouch, arm still out
        pelvis=(0.1, -2.05, 2.55), hips=20, twist=-60, bend=33, lclav=-20,
        lhand=(0.4, -7.7, 3.6), rhand=(-0.9, -2.2, 6.2), sword=(-0.3, 0.7, 0.65),
        lfoot=L0, rfoot=R_FWD),
    18: dict(  # classic 10: right foot lifting off to step back, body rising
        pelvis=(0.12, -1.5, 2.9), hips=12, twist=-30, bend=15,
        lhand=(1.0, -4.0, 4.1), rhand=(-1.2, -0.8, 5.4), sword=(-0.5, 0.2, 0.5),
        lfoot=L0, rfoot=(-0.65, -2.3, 0.8)),
    20: dict(  # classic 11: right foot passing back beside the left, almost upright
        pelvis=(0.15, -0.6, 3.4), hips=4, twist=-8, bend=5,
        lhand=(1.4, -1.6, 3.9), rhand=(-1.3, -0.4, 4.3),
        lfoot=L0, rfoot=(-0.6, 0.2, 0.8)),
    LAST: None,  # back to ready (loops into the next attack/idle)
}

for f, k in KEYS.items():
    scene.frame_set(f)
    reset_to_base()
    if k:
        move_to("pelvis_bind_jnt", k["pelvis"])
        if k.get("hips"):
            rotate("pelvis_bind_jnt", (0, 0, 1), k["hips"])
        torso(k.get("twist", 0), k.get("bend", 0), k.get("lean", 0))
        if k.get("lclav"):  # left collarbone: negative swings the shoulder joint forward
            rotate("L_shoulder_bind_jnt", (0, 0, 1), k["lclav"])
        # keep the head looking roughly forward
        rotate("neck_bind_jnt", (0, 0, 1), -0.5 * (k.get("twist", 0) + k.get("hips", 0)))
        rotate("neck_bind_jnt", (1, 0, 0), -0.5 * k.get("bend", 0))
    for pb in pbs:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion", frame=f)
    for key, e in T.items():
        if k:
            e.location = k[key]
        else:
            e.location = head_of({"lfoot": "L_leg_03_bind_jnt", "rfoot": "R_leg_03_bind_jnt",
                                  "lhand": "L_hand_bind_jnt", "rhand": "R_hand_bind_jnt"}[key])
        e.keyframe_insert("location", frame=f)
        IK[key].influence = 1.0 if k else 0.0
        IK[key].keyframe_insert("influence", frame=f)

# The IK solver (with the twist bones locked) can settle a little off target; nudge each foot target by
# its miss at every key so the feet land where they should and don't sink into the floor.
FOOT_BONE = {"lfoot": "L_leg_03_bind_jnt", "rfoot": "R_leg_03_bind_jnt"}
for _ in range(3):
    for f, k in KEYS.items():
        if not k:
            continue
        scene.frame_set(f)
        for key, bone in FOOT_BONE.items():
            miss = Vector(k[key]) - pbs[bone].matrix.translation
            T[key].location = T[key].location + miss
            T[key].keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- bake to plain keys
FEET = {"L_leg_03_bind_jnt", "R_leg_03_bind_jnt"}
SUBTREE = {pb.name: [pb.name] + [c.name for c in pb.children_recursive] for pb in pbs}


def set_with_children(mats, name, m):
    """Give bone `name` world matrix m and carry everything attached to it along."""
    delta = m @ mats[name].inverted()
    for n in SUBTREE[name]:
        mats[n] = delta @ mats[n]


# Sword direction (direction the R_weapon_attach +Y axis points): keyed on some poses, faded to the
# natural wrist on the others.
SWORD = sorted((f, Vector(k["sword"]).normalized() if k and "sword" in k else None) for f, k in KEYS.items())


def sword_at(f):
    prev = max((kf for kf in SWORD if kf[0] <= f), key=lambda kf: kf[0])
    nxt = min((kf for kf in SWORD if kf[0] >= f), key=lambda kf: kf[0])
    u = 0.0 if nxt[0] == prev[0] else (f - prev[0]) / (nxt[0] - prev[0])
    w = (1 - u) * (prev[1] is not None) + u * (nxt[1] is not None)
    a, b = prev[1] or nxt[1], nxt[1] or prev[1]
    if a is None:
        return 0.0, None
    return w, a.slerp(b, u) if a.dot(b) < 0.9999 else a


baked = {}
for f in range(0, LAST + 1):
    scene.frame_set(f)
    mats = {pb.name: pb.matrix.copy() for pb in pbs}
    w, d = sword_at(f)
    if w > 0:
        hand = mats["R_hand_bind_jnt"]
        cur = mats["R_weapon_attach"].col[1].xyz.normalized()
        q = Quaternion().slerp(cur.rotation_difference(d), w)
        pivot = hand.translation.copy()
        set_with_children(mats, "R_hand_bind_jnt",
                          Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ hand)
    for n in FEET:  # feet keep the ready-stance orientation, just move them...
        m = base_world[n].copy()
        if n == "R_leg_03_bind_jnt":
            # ...except the right foot: in the ready stance it is the back foot, toed out and pitched down.
            # As it strides in front, turn the toes forward and lay it flat like the left foot.
            pos = mats[n].translation
            t = max(0.0, min(1.0, (R0.y - pos.y) / (R0.y - R_FWD[1])))
            toe = base_world["R_leg_04_bind_jnt"].translation - base_world[n].translation
            pitch = math.radians(25)
            target = Vector((0, -math.cos(pitch), -math.sin(pitch))) * toe.length
            q = Quaternion().slerp(toe.rotation_difference(target), t)
            m = q.to_matrix().to_4x4() @ m.to_3x3().to_4x4()
        m.translation = mats[n].translation
        set_with_children(mats, n, m)
    baked[f] = mats
    if f in (9, 13):
        fa = (mats["R_hand_bind_jnt"].translation - mats["R_lwr_arm_bind_jnt"].translation).normalized()
        sw = mats["R_weapon_attach"].col[1].xyz.normalized()
        print(f"frame {f:2d}: sword dir {tuple(round(c, 2) for c in sw)}  forearm-to-sword angle {math.degrees(fa.angle(sw)):.0f} deg")
    if f in (0, 4, 8, 13, 18, 22):
        fmt = lambda v: "(" + ", ".join(f"{c:.2f}" for c in v) + ")"
        print(f"frame {f:2d}: L ankle {fmt(mats['L_leg_03_bind_jnt'].translation)}  "
              f"R ankle {fmt(mats['R_leg_03_bind_jnt'].translation)}  pelvis {fmt(mats['pelvis_bind_jnt'].translation)}")
    if f == 13:
        s, e, w = (mats[n].translation for n in ("L_upr_arm_bind_jnt", "L_lwr_arm_bind_jnt", "L_hand_bind_jnt"))
        elbow = math.degrees((s - e).angle(w - e))
        print(f"hit frame: L elbow angle {elbow:.0f} deg (180 = straight), wrist {tuple(round(c, 2) for c in w)}, "
              f"shoulder {tuple(round(c, 2) for c in s)}")

for pb in pbs:
    for c in list(pb.constraints):
        pb.constraints.remove(c)
for e in T.values():
    bpy.data.objects.remove(e)
# drop the original clip and the keying scratch action so only the baked one is exported
for act in list(bpy.data.actions):
    bpy.data.actions.remove(act)
arm.animation_data.action = bpy.data.actions.new("1hs_skill1")

order = []
def visit(pb):
    order.append(pb)
    for c in pb.children:
        visit(c)
for pb in pbs:
    if pb.parent is None:
        visit(pb)

for f, mats in baked.items():
    for pb in order:
        rest = pb.bone.matrix_local
        if pb.parent:
            prest = pb.parent.bone.matrix_local
            basis = (mats[pb.parent.name] @ prest.inverted() @ rest).inverted() @ mats[pb.name]
        else:
            basis = rest.inverted() @ mats[pb.name]
        loc, rot, _ = basis.decompose()
        pb.location = loc
        pb.rotation_quaternion = rot
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion", frame=f)

scene.frame_start, scene.frame_end = 0, LAST
if blend_out:
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
# the splice only needs the skeleton animation; LSLib's importer chokes on Blender's re-exported meshes
for o in list(bpy.data.objects):
    if o.type == "MESH":
        bpy.data.objects.remove(o)
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_animations=True)
print("exported", dst)

# The game plants the feet with its own foot IK, aimed by the clip's L/R_IK_position vector tracks
# (ankle positions). splice.ps1 rewrites those tracks from this file so the feet follow this animation.
feet = {"fps": scene.render.fps, "frames": [
    {"t": f / scene.render.fps,
     "L": list(L0),  # the left foot never moves; pin it exactly (the baked IK drifts slightly between keys)
     "R": list(mats["R_leg_03_bind_jnt"].translation)}
    for f, mats in sorted(baked.items())]}
with open(dst + ".feet.json", "w") as fp:
    json.dump(feet, fp, indent=1)
print("wrote", dst + ".feet.json")

"""LSLib writes animation samplers as STEP; switch them to LINEAR so Blender plays the motion smoothly.

usage: python linear_gltf.py <lslib_export.gltf-as-.glb> <out.gltf>
(LSLib's ".glb" here is JSON text with an external .bin; the output keeps pointing at that .bin,
so write it next to the input.)
"""
import json, sys

doc = json.load(open(sys.argv[1], encoding="utf-8"))
n = 0
for anim in doc.get("animations", []):
    for s in anim["samplers"]:
        if s.get("interpolation") == "STEP":
            s["interpolation"] = "LINEAR"
            n += 1
json.dump(doc, open(sys.argv[2], "w", encoding="utf-8"), separators=(",", ":"))
print(f"{n} samplers -> LINEAR, wrote {sys.argv[2]}")

"""Copy LSLib's EXT_lslib_profile scene extension (bone order etc.) into a Blender .glb.

Blender drops unknown glTF extensions, and LSLib's importer needs this one.
usage: python fix_glb.py <lslib_export.glb|.gltf> <blender.glb> <out.glb>
"""
import json, struct, sys


def load(path):
    b = open(path, "rb").read()
    if b[:4] != b"glTF":
        return json.loads(b), None
    chunks, off = [], 12
    while off < len(b):
        n, kind = struct.unpack_from("<II", b, off)
        chunks.append((kind, b[off + 8:off + 8 + n]))
        off += 8 + n
    return json.loads(chunks[0][1]), chunks[1:]


def save(path, doc, rest):
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js
    for kind, data in rest:
        body += struct.pack("<II", len(data), kind) + data
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)


ref, _ = load(sys.argv[1])
doc, rest = load(sys.argv[2])
ext = ref["scenes"][0]["extensions"]["EXT_lslib_profile"]
doc["scenes"][doc.get("scene", 0)].setdefault("extensions", {})["EXT_lslib_profile"] = ext
used = doc.setdefault("extensionsUsed", [])
if "EXT_lslib_profile" not in used:
    used.append("EXT_lslib_profile")
save(sys.argv[3], doc, rest)
print("wrote", sys.argv[3])

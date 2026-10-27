"""Find each mesh's Word4 vertex buffer in the raw section dumps and report its w component.
usage: python word4_w.py <raw dir>
"""
import json, os, struct, sys
from collections import Counter

d = sys.argv[1]
scales = {}
for t in json.load(open(os.path.join(d, "targets.json"), encoding="utf-8-sig")):
    raw = open(os.path.join(d, t["part"] + ".sec0"), "rb").read()
    tx, ty, tz = (round(t[k] * 32767) for k in "xyz")
    w = None
    for off in range(0, len(raw) - 8, 2):
        x, y, z = struct.unpack_from("<3h", raw, off)
        if abs(x - tx) <= 1 and abs(y - ty) <= 1 and abs(z - tz) <= 1:
            # stride: next vertex is 28 bytes on for PWWHT442; verify w is constant along the buffer
            ws = Counter(struct.unpack_from("<h", raw, off + 6 + k * 28)[0] for k in range(min(t["count"], (len(raw) - off - 8) // 28)))
            w = ws.most_common(2)
            break
    main = w[0][0] if w else None
    print(f"{t['part']:18s} {t['mesh']:26s} verts={t['count']:6d} w={w}  w/1024={main / 1024 if main else 0:.3f}")
    if main:
        # LSLib reads Word4 positions as xyz/32767 and drops w; real position = that * w/1024
        scales[f"{t['part']}/{t['mesh']}"] = main / 1024
json.dump(scales, open(os.path.join(d, "scales.json"), "w"), indent=1)

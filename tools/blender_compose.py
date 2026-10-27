# Stack image strips (scaled to the same width) into one comparison sheet.
# blender -b --factory-startup -P blender_compose.py -- <out.png> <strip1.png> <strip2.png> ...
import sys
import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
out, strips = args[0], args[1:]
W = 2400
rows = []
for p in strips:
    img = bpy.data.images.load(p)
    w, h = img.size
    img.scale(W, max(1, round(h * W / w)))
    a = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    a[..., 3] = 1.0
    rows.append(a)
    rows.append(np.full((6, W, 4), (1.0, 0.8, 0.0, 1.0), dtype=np.float32))  # separator
rows = rows[:-1]
sheet = np.concatenate(rows[::-1], axis=0)  # Blender images are bottom-up: first strip on top
img = bpy.data.images.new("sheet", W, sheet.shape[0], alpha=True)
img.pixels = sheet.ravel()
img.filepath_raw = out
img.file_format = "PNG"
img.save()
print("wrote", out)

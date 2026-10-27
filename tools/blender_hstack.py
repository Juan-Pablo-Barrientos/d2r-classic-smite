# blender -b -P blender_hstack.py -- <out.png> <img1> <img2> ...  (same-size images side by side)
import sys, bpy, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
imgs = []
for p in a[1:]:
    im = bpy.data.images.load(p)
    imgs.append(np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4))
sheet = np.concatenate(imgs, axis=1)
out = bpy.data.images.new("s", sheet.shape[1], sheet.shape[0], alpha=True)
out.pixels = sheet.ravel(); out.filepath_raw = a[0]; out.file_format = "PNG"; out.save()
print("wrote", a[0])

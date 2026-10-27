"""Render the original Smite sprite in sync with an in-game capture.

For each output time (from..to by step ms) picks the classic frame whose phase matches the capture:
every capture hit time lines up with the sprite's hit frame (COF trigger, frame 7 of 12), and each
attack spans `period` ms. Before the first attack the sprite stands on frame 0.

usage: python dcc_sync.py <classic data/global dir> <out dir> --dir 4 --hits 965,1395,... --period 438
                          --from 600 --to 2340 --step 40 [--size 290x340 --feet 145,293 --height 215]
"""
import argparse, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dcc  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("globaldir"); ap.add_argument("outdir")
ap.add_argument("--dir", type=int, default=4)
ap.add_argument("--hits", required=True); ap.add_argument("--period", type=float, required=True)
ap.add_argument("--from", dest="t0", type=int, required=True); ap.add_argument("--to", dest="t1", type=int, required=True)
ap.add_argument("--step", type=int, default=40)
ap.add_argument("--size", default="290x340"); ap.add_argument("--feet", default="145,293")
ap.add_argument("--height", type=float, default=215)
ap.add_argument("--bg", default="22,24,28")
a = ap.parse_args()

W, H = (int(v) for v in a.size.split("x")); OX, OY = (int(v) for v in a.feet.split(","))
BG = bytes(int(v) for v in a.bg.split(","))
g = a.globaldir
files = {"hd": "hd/pahdlits11hs", "tr": "tr/patrlits11hs", "lg": "lg/palglits11hs", "ra": "ra/paralits11hs",
         "la": "la/palalits11hs", "rh": "rh/parhscms11hs", "sh": "sh/pashkits11hs",
         "s1": "s1/pas1lits11hs", "s2": "s2/pas2lits11hs"}
pal = open(os.path.join(g, "palette/act1/pal.dat"), "rb").read()
cof = os.path.join(g, "chars/pa/cof/pas11hs.cof")
layers, nf, nd, triggers, order = dcc.load_cof(cof)
HIT = triggers.index(1)
sprites = {c: dcc.load_dcc(os.path.join(g, "chars/pa", f + ".dcc"))[0] for c, f in files.items()}


def compose(fi):
    """{(x, y): palette index} in sprite space (origin at the feet) for frame fi."""
    px = {}
    for comp in order[a.dir][fi]:
        name = dcc.COMP[comp]
        if name not in sprites:
            continue
        left, top, w, h, frames = sprites[name][a.dir]
        img = frames[fi]
        for y in range(h):
            for x in range(w):
                v = img[x + y * w]
                if v:
                    px[(left + x, top + y)] = v
    return px


frames = [compose(fi) for fi in range(nf)]
ys = [y for (x, y) in frames[0]]
scale = a.height / (max(ys) - min(ys) + 1)  # standing height -> HD Paladin's height on screen
xs = [x for (x, y) in frames[0]]
cx = (min(xs) + max(xs)) / 2  # centre the standing body horizontally on the feet position


def render(fi, path):
    src = frames[fi]
    rgb = bytearray(BG * (W * H))
    for Y in range(H):
        sy = int((Y - OY) / scale + 0.5)
        for X in range(W):
            v = src.get((int((X - OX) / scale + cx + 0.5), sy))
            if v:
                o = (Y * W + X) * 3
                rgb[o:o + 3] = bytes((pal[v * 3 + 2], pal[v * 3 + 1], pal[v * 3]))
    dcc.write_png(path, W, H, rgb)


hits = [float(h) for h in a.hits.split(",")]
starts = [h - HIT / nf * a.period for h in hits]  # attack i starts here...
os.makedirs(a.outdir, exist_ok=True)
cache = {}
picked = []
for i, t in enumerate(range(a.t0, a.t1 + 1, a.step)):
    fi = 0
    for k in range(len(hits) - 1):
        s, h, e = starts[k], hits[k], starts[k + 1]  # ...and ends where attack i+1 starts
        if s <= t < h:  # frames 0..HIT stretched over [start, hit]
            fi = int((t - s) / (h - s) * HIT)
        elif h <= t < e:  # frames HIT..nf stretched over [hit, next start]
            fi = min(nf - 1, HIT + int((t - h) / (e - h) * (nf - HIT)))
    picked.append(fi)
    if fi not in cache:
        cache[fi] = os.path.join(a.outdir, f"sprite_{fi:02d}.png")
        render(fi, cache[fi])
    with open(cache[fi], "rb") as src, open(os.path.join(a.outdir, f"left_{i:03d}.png"), "wb") as dst:
        dst.write(src.read())
print(f"scale {scale:.2f}, hit frame {HIT}, {len(picked)} frames:", " ".join(map(str, picked)))

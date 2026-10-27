"""Minimal Diablo II DCC decoder + COF compositor -> PNG contact sheet.

Follows Paul Siramy's DCC notes / OpenDiablo2's implementation.
usage: python dcc.py <classic data/global dir> <out.png>
"""
import os, struct, sys, zlib

CRAZY = [0, 1, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 26, 28, 30, 32]
MASK_BITS = [0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4]


class Bits:
    def __init__(self, data, pos=0):
        self.d, self.pos = data, pos  # pos in bits, LSB first

    def get(self, n):
        v = 0
        for i in range(n):
            byte = self.d[self.pos >> 3]
            v |= ((byte >> (self.pos & 7)) & 1) << i
            self.pos += 1
        return v

    def sget(self, n):
        v = self.get(n)
        if n and v & (1 << (n - 1)):
            v -= 1 << n
        return v


class Frame:
    pass


def split_cells(start, size, origin):
    """Widths of the 4px cells a frame spans, given its offset from the direction box."""
    first = 4 - ((start - origin) % 4)
    if size - first <= 1:
        n = 1
    else:
        tmp = size - first - 1
        n = 2 + tmp // 4
        if tmp % 4 == 0:
            n -= 1
    if n == 1:
        return [size]
    return [first] + [4] * (n - 2) + [size - first - 4 * (n - 2)]


def decode_direction(data, off, nframes):
    b = Bits(data, off * 8)
    b.get(32)  # outsize coded
    comp = b.get(2)
    v0b, wb, hb, xb, yb, ob, cb = (CRAZY[b.get(4)] for _ in range(7))
    frames = []
    for _ in range(nframes):
        f = Frame()
        b.get(v0b)
        f.w, f.h = b.get(wb), b.get(hb)
        f.x, f.y = b.sget(xb), b.sget(yb)
        f.opt = b.get(ob)
        b.get(cb)
        if b.get(1):
            raise ValueError("bottom-up frames unsupported")
        f.left, f.top = f.x, f.y - f.h + 1
        frames.append(f)
    if ob:
        b.pos = (b.pos + 7) & ~7
        b.pos += 8 * sum(f.opt for f in frames)
    eq_size = b.get(20) if comp & 2 else 0
    pm_size = b.get(20)
    et_size = rp_size = 0
    if comp & 1:
        et_size, rp_size = b.get(20), b.get(20)
    pal = [i for i in range(256) if b.get(1)]

    ec = Bits(data, b.pos)
    pm = Bits(data, ec.pos + eq_size)
    et = Bits(data, pm.pos + pm_size)
    rp = Bits(data, et.pos + et_size)
    pcd = Bits(data, rp.pos + rp_size)

    left = min(f.left for f in frames)
    top = min(f.top for f in frames)
    right = max(f.left + f.w for f in frames)
    bottom = max(f.top + f.h for f in frames)
    W, H = right - left, bottom - top
    hcells, vcells = 1 + (W - 1) // 4, 1 + (H - 1) // 4

    # frame cells (positions relative to the direction box)
    for f in frames:
        ws = split_cells(f.left, f.w, left)
        hs = split_cells(f.top, f.h, top)
        f.hc, f.vc = len(ws), len(hs)
        f.cells = []
        y = f.top - top
        for ch in hs:
            x = f.left - left
            for cw in ws:
                f.cells.append((x, y, cw, ch))
                x += cw
            y += ch

    # stage 1: pixel buffer
    pbuf = []  # [values(4), frame, cellindex]
    cellbuf = [None] * (hcells * vcells)
    for fi, f in enumerate(frames):
        ox, oy = (f.left - left) // 4, (f.top - top) // 4
        for cy in range(f.vc):
            for cx in range(f.hc):
                cur = ox + cx + (oy + cy) * hcells
                if cellbuf[cur] is not None:
                    if eq_size and ec.get(1):
                        continue
                    mask = pm.get(4)
                else:
                    mask = 0xF
                stack = [0, 0, 0, 0]
                last = 0
                nbits = MASK_BITS[mask]
                enc = et.get(1) if nbits and et_size else 0
                decoded = 0
                for i in range(nbits):
                    if enc:
                        stack[i] = rp.get(8)
                    else:
                        stack[i] = last
                        d = pcd.get(4)
                        stack[i] += d
                        while d == 15:
                            d = pcd.get(4)
                            stack[i] += d
                    if stack[i] == last:
                        stack[i] = 0
                        break
                    last = stack[i]
                    decoded += 1
                old = cellbuf[cur]
                vals = [0, 0, 0, 0]
                idx = decoded - 1
                for i in range(4):
                    if mask & (1 << i):
                        if idx >= 0:
                            vals[i] = stack[idx]
                            idx -= 1
                    else:
                        vals[i] = old[0][i]
                entry = [vals, fi, cx + cy * f.hc]
                pbuf.append(entry)
                cellbuf[cur] = entry
    for e in pbuf:
        e[0] = [pal[v] if v < len(pal) else 0 for v in e[0]]

    # stage 2: frames
    canvas = bytearray(W * H)
    last = {}  # dir cell -> (w, h, x, y)
    out = []
    pi = 0
    for fi, f in enumerate(frames):
        img = bytearray(W * H)
        for c, (x, y, cw, ch) in enumerate(f.cells):
            dcell = x // 4 + (y // 4) * hcells
            e = pbuf[pi] if pi < len(pbuf) else None
            if e is None or e[1] != fi or e[2] != c:
                lw = last.get(dcell)
                if lw is None or lw[0] != cw or lw[1] != ch:
                    for yy in range(ch):
                        for xx in range(cw):
                            canvas[x + xx + (y + yy) * W] = 0
                else:
                    for yy in range(ch):
                        for xx in range(cw):
                            v = canvas[lw[2] + xx + (lw[3] + yy) * W]
                            canvas[x + xx + (y + yy) * W] = v
                            img[x + xx + (y + yy) * W] = v
            else:
                v = e[0]
                if v[0] == v[1]:
                    for yy in range(ch):
                        for xx in range(cw):
                            canvas[x + xx + (y + yy) * W] = v[0]
                else:
                    nb = 2 if v[1] != v[2] else 1
                    for yy in range(ch):
                        for xx in range(cw):
                            canvas[x + xx + (y + yy) * W] = v[pcd.get(nb)]
                for yy in range(ch):
                    for xx in range(cw):
                        img[x + xx + (y + yy) * W] = canvas[x + xx + (y + yy) * W]
                pi += 1
            last[dcell] = (cw, ch, x, y)
        out.append(img)
    return left, top, W, H, out


def load_dcc(path):
    d = open(path, "rb").read()
    sig, ver, ndirs, nframes = struct.unpack_from("<BBBI", d, 0)
    assert sig == 0x74, path
    offs = struct.unpack_from(f"<{ndirs}I", d, 15)
    return [decode_direction(d, o, nframes) for o in offs], nframes


def load_cof(path):
    d = open(path, "rb").read()
    nl, nf, nd = d[0], d[1], d[2]
    layers = []
    p = 28
    for _ in range(nl):
        layers.append(d[p])
        p += 9
    triggers = list(d[p:p + nf])
    p += nf
    order = [[list(d[p + (di * nf + fi) * nl:p + (di * nf + fi + 1) * nl]) for fi in range(nf)] for di in range(nd)]
    return layers, nf, nd, triggers, order


def write_png(path, w, h, rgb):
    raw = b"".join(b"\0" + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    chunk = lambda t, b: struct.pack(">I", len(b)) + t + b + struct.pack(">I", zlib.crc32(t + b) & 0xFFFFFFFF)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


COMP = ["hd", "tr", "lg", "ra", "la", "rh", "lh", "sh", "s1", "s2"]


def main():
    g, out = sys.argv[1], sys.argv[2]
    files = {"hd": "hd/pahdlits11hs", "tr": "tr/patrlits11hs", "lg": "lg/palglits11hs", "ra": "ra/paralits11hs",
             "la": "la/palalits11hs", "rh": "rh/parhscms11hs", "sh": "sh/pashkits11hs",
             "s1": "s1/pas1lits11hs", "s2": "s2/pas2lits11hs"}
    pal = open(os.path.join(g, "palette/act1/pal.dat"), "rb").read()
    layers, nf, nd, triggers, order = load_cof(os.path.join(g, "chars/pa/cof/pas11hs.cof"))
    print("cof layers", [COMP[l] for l in layers], "frames", nf, "dirs", nd, "trigger frames", [i for i, t in enumerate(triggers) if t])
    dcc = {c: load_dcc(os.path.join(g, "chars/pa", f + ".dcc"))[0] for c, f in files.items()}

    dirs = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "4,0,5,1").split(",")]
    # fixed cell around the origin from the COF bounding box
    bl, br, bt, bb = struct.unpack_from("<4i", open(os.path.join(g, "chars/pa/cof/pas11hs.cof"), "rb").read(), 8)
    cw, ch = br - bl, bb - bt
    scale = 2
    SW, SH = cw * nf * scale, ch * len(dirs) * scale
    rgb = bytearray([40, 40, 48] * SW * SH)
    for row, di in enumerate(dirs):
        for fi in range(nf):
            for comp in order[di][fi]:
                name = COMP[comp]
                if name not in dcc:
                    continue
                left, top, W, H, frames = dcc[name][di]
                img = frames[fi]
                for y in range(H):
                    for x in range(W):
                        v = img[x + y * W]
                        if not v:
                            continue
                        px, py = left + x - bl, top + y - bt
                        if not (0 <= px < cw and 0 <= py < ch):
                            continue
                        r, gg, bcol = pal[v * 3 + 2], pal[v * 3 + 1], pal[v * 3]
                        for sy in range(scale):
                            for sx in range(scale):
                                X = (fi * cw + px) * scale + sx
                                Y = (row * ch + py) * scale + sy
                                o = (Y * SW + X) * 3
                                rgb[o:o + 3] = bytes((r, gg, bcol))
            # frame separator + mark the hit frame
            for y in range(row * ch * scale, (row + 1) * ch * scale):
                o = (y * SW + fi * cw * scale) * 3
                rgb[o:o + 3] = b"\xff\xd0\x00" if triggers[fi] else b"\x60\x60\x70"
    write_png(out, SW, SH, rgb)
    print("wrote", out, SW, SH)


if __name__ == "__main__":
    main()

"""Crop the lower body of each classic frame from a dcc.py strip, enlarged, with a grid for measuring.
usage: python crop_feet.py <strip.png> <out.png>"""
import sys, zlib, struct
def read(p):
    d = open(p, 'rb').read(); i = 8; idat = b''
    while i < len(d):
        n, t = struct.unpack('>I4s', d[i:i + 8]); b = d[i + 8:i + 8 + n]; i += 12 + n
        if t == b'IHDR': w, h = struct.unpack('>II', b[:8])
        if t == b'IDAT': idat += b
    raw = zlib.decompress(idat); s = w * 3 + 1
    return w, h, b''.join(raw[y * s + 1:(y + 1) * s] for y in range(h))
def write(p, W, H, rgb):
    raw = b''.join(b'\0' + bytes(rgb[y * W * 3:(y + 1) * W * 3]) for y in range(H))
    c = lambda t, b: struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    open(p, 'wb').write(b'\x89PNG\r\n\x1a\n' + c(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) + c(b'IDAT', zlib.compress(raw, 6)) + c(b'IEND', b''))
w, h, px = read(sys.argv[1]); cw = w // 12
x0, x1, y0, y1 = int(cw * .2), int(cw * .9), int(h * .5), int(h * .92); tw, th = x1 - x0, y1 - y0
Z = 2; cols = 6
W, H = tw * Z * cols, th * Z * 2; out = bytearray(W * H * 3)
for f in range(12):
    gx, gy = (f % cols) * tw * Z, (f // cols) * th * Z
    for y in range(th):
        for x in range(tw):
            o = ((y0 + y) * w + f * cw + x0 + x) * 3; rgb = px[o:o + 3]
            if x % 20 == 0 or y % 20 == 0:  # light grid every 10 source pixels (scale 2 sheet) to read positions
                if rgb == b'\x28\x28\x30': rgb = b'\x40\x40\x4c'
            for sy in range(Z):
                d = ((gy + y * Z + sy) * W + gx + x * Z) * 3
                out[d:d + Z * 3] = rgb * Z
    for y in range(th * Z):  # frame border
        d = ((gy + y) * W + gx) * 3; out[d:d + 3] = b'\xa0\xa0\x30'
write(sys.argv[2], W, H, out); print(W, H)

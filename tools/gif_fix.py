"""Give a multi-frame GIF a per-frame delay and make it loop forever.

usage: python gif_fix.py <in.gif> <out.gif> <delay in 1/100 s>
Adds a NETSCAPE2.0 loop extension after the header and a Graphic Control Extension (delay,
dispose = leave in place) before every image, replacing any existing ones.
"""
import struct
import sys

src, dst, delay = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = open(src, "rb").read()
assert d[:6] in (b"GIF87a", b"GIF89a"), "not a GIF"
flags = d[10]
p = 13 + (3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0)  # header + logical screen + global table
out = bytearray(b"GIF89a" + d[6:p])
out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"  # loop forever


def skip_sub_blocks(i):
    while d[i]:
        i += d[i] + 1
    return i + 1


frames = 0
while p < len(d):
    b = d[p]
    if b == 0x3B:  # trailer
        break
    if b == 0x21:  # extension: drop existing graphic control / loop blocks, keep others
        label = d[p + 1]
        end = skip_sub_blocks(p + 2)
        if label not in (0xF9, 0xFF):
            out += d[p:end]
        p = end
    elif b == 0x2C:  # image descriptor
        fl = d[p + 9]
        q = p + 10 + (3 * 2 ** ((fl & 7) + 1) if fl & 0x80 else 0)
        end = skip_sub_blocks(q + 1)  # LZW min code size, then data sub-blocks
        out += b"\x21\xf9\x04" + bytes([0x04]) + struct.pack("<H", delay) + b"\x00\x00"
        out += d[p:end]
        frames += 1
        p = end
    else:
        raise ValueError(f"unexpected block 0x{b:02x} at {p}")
out += b"\x3b"
open(dst, "wb").write(out)
print(f"wrote {dst}: {frames} frames, {delay / 100:.2f}s each, {len(out) // 1024} KB")

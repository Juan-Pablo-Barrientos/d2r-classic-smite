"""List / extract files from D2R CASC storage via D2RMM's CascLib.dll.

usage: python casc.py list <regex>
       python casc.py extract <regex> <outdir>
Set D2R_GAME to the game folder (the one with .build.info) and CASCLIB to D2RMM's tools\\CascLib.dll.
"""
import ctypes, os, re, sys
from ctypes import wintypes as wt

DLL = os.environ.get("CASCLIB") or sys.exit("set CASCLIB to D2RMM's tools\\CascLib.dll")
GAME = os.environ.get("D2R_GAME") or sys.exit("set D2R_GAME to the Diablo II: Resurrected folder")

casc = ctypes.WinDLL(DLL)
H = ctypes.c_void_p


def open_storage():
    h = H()
    # D2RMM's CascLib build is ANSI: LPCTSTR is char*
    casc.CascOpenStorage.restype = ctypes.c_bool
    if not casc.CascOpenStorage(GAME.encode(), 0, ctypes.byref(h)):
        raise OSError(f"CascOpenStorage failed: {ctypes.GetLastError()}")
    return h


def iter_names(h):
    buf = ctypes.create_string_buffer(4096)  # CASC_FIND_DATA, generously sized
    casc.CascFindFirstFile.restype = H
    f = casc.CascFindFirstFile(h, b"*", buf, None)
    if not f:
        raise OSError(f"CascFindFirstFile failed: {ctypes.GetLastError()}")
    casc.CascFindNextFile.restype = ctypes.c_bool
    try:
        while True:
            name = buf.raw[:260].split(b"\0", 1)[0].decode("utf-8", "replace")
            if not name:  # this build keeps "succeeding" with empty entries at the end
                break
            # szFileName[260], CKey[16], EKey[16], TagBitMask (8, aligned), FileSize
            yield name, int.from_bytes(buf.raw[296:304], "little")
            if not casc.CascFindNextFile(H(f), buf):
                break
    finally:
        casc.CascFindClose(H(f))


def read_file(h, name):
    fh = H()
    if not casc.CascOpenFile(h, name.encode(), 0, 0, ctypes.byref(fh)):
        raise OSError(f"CascOpenFile failed for {name}: {ctypes.GetLastError()}")
    out = bytearray()
    chunk = ctypes.create_string_buffer(1 << 20)
    got = wt.DWORD()
    try:
        while casc.CascReadFile(fh, chunk, len(chunk), ctypes.byref(got)) and got.value:
            out += chunk.raw[:got.value]
    finally:
        casc.CascCloseFile(fh)
    return bytes(out)


def main():
    cmd, pat = sys.argv[1], re.compile(sys.argv[2], re.I)
    h = open_storage()
    try:
        hits = [(n, s) for n, s in iter_names(h) if pat.search(n)]
        if cmd == "list":
            for n, s in hits:
                print(f"{s:>10}  {n}")
            print(f"{len(hits)} files")
        elif cmd == "extract":
            outdir = sys.argv[3]
            for n, _ in hits:
                rel = n.split(":", 1)[-1].replace("\\", "/").lstrip("/")
                dst = os.path.join(outdir, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as fp:
                    fp.write(read_file(h, n))
                print(dst)
            print(f"{len(hits)} files extracted")
    finally:
        casc.CascCloseStorage(h)


main()

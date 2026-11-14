#!/usr/bin/env python3
"""Remap ODBC32 ANSI 'xxxA' ordinal imports (stubs in Wine 10) to the plain ANSI ordinal (A - 200).
usage: patch_odbc.py file.exe...   (in place; idempotent)"""
import struct, sys

A_TO_PLAIN = {211: 11, 219: 19, 236: 36, 240: 40, 241: 41, 254: 54, 260: 60}  # ExecDirect,Prepare,GetDiagRec,Columns,DriverConnect,Tables,ForeignKeys

def patch(path):
    d = bytearray(open(path, 'rb').read())
    pe = struct.unpack_from('<I', d, 60)[0]; oh = pe + 24
    ns = struct.unpack_from('<H', d, pe + 6)[0]; so = oh + struct.unpack_from('<H', d, pe + 20)[0]
    secs = [struct.unpack_from('<IIII', d, so + 40 * i + 8) for i in range(ns)]
    def off(r):
        for vs, va, rs, rp in secs:
            if va <= r < va + max(vs, rs): return r - va + rp
    o = off(struct.unpack_from('<I', d, oh + 104)[0]); n = 0
    while True:
        oft, _, _, nm, ft = struct.unpack_from('<5I', d, o); o += 20
        if not nm: break
        if d[off(nm):d.index(0, off(nm))].upper() != b'ODBC32.DLL': continue
        for arr in {oft, ft} - {0}:
            t = off(arr)
            while (e := struct.unpack_from('<I', d, t)[0]):
                if e & 0x80000000 and (e & 0xffff) in A_TO_PLAIN:
                    struct.pack_into('<I', d, t, 0x80000000 | A_TO_PLAIN[e & 0xffff]); n += 1
                t += 4
    if n: open(path, 'wb').write(d)
    print(f'{path}: {n} odbc thunks remapped')

if __name__ == '__main__':
    for p in sys.argv[1:]: patch(p)

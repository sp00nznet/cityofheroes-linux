#!/usr/bin/env python3
"""Raise the servers' network-loop wait from 1 ms to IDLE_MS.

The network wait (GetQueuedCompletionStatus with a 1 ms timeout): the main loops wake ~500x/s. On Windows
that's free; under Wine every wake is a wineserver round-trip (~2 cores idle for the shard).
The IOCP wait still returns the moment network I/O completes, so only timer work slows to ~50 Hz.
The compiler inlined the 1 as `mov reg, 1` shortly before the GQCS call; we patch that immediate.
Usage: patch_idle.py [--dry] EXE...   (idempotent; IDLE_MS env, default 20)
"""
import os, re, struct, sys

ms = int(os.environ.get('IDLE_MS', '20'))
sleep_ms = int(os.environ.get('SLEEP_MS', '10'))
dry = '--dry' in sys.argv
for f in [a for a in sys.argv[1:] if a != '--dry']:
    b = bytearray(open(f, 'rb').read())
    pe = struct.unpack_from('<I', b, 0x3c)[0]
    base = struct.unpack_from('<I', b, pe + 0x34)[0]
    nsec = struct.unpack_from('<H', b, pe + 6)[0]
    opt = struct.unpack_from('<H', b, pe + 0x14)[0]
    secs = [struct.unpack_from('<8sIIII', b, pe + 0x18 + opt + 40 * i) for i in range(nsec)]
    def off(rva):
        for _, vs, va, rs, ro in secs:
            if va <= rva < va + max(vs, rs): return rva - va + ro
    imp_rva = struct.unpack_from('<I', b, pe + 0x18 + 0x68)[0]
    iat = {}
    d = off(imp_rva)
    while struct.unpack_from('<I', b, d + 12)[0]:
        oft, _, _, _, ft = struct.unpack_from('<IIIII', b, d)
        t, i = off(oft or ft), 0
        while (e := struct.unpack_from('<I', b, t + 4 * i)[0]):
            if not e & 0x80000000:
                iat[bytes(b[off(e) + 2:b.index(0, off(e) + 2)])] = base + ft + 4 * i
            i += 1
        d += 20
    done = []
    gqcs = iat.get(b'GetQueuedCompletionStatus')
    if gqcs:
        for m in re.finditer(re.escape(b'\xff\x15' + struct.pack('<I', gqcs)), b):
            win = b[m.start() - 0x60:m.start()]
            # mov edi/esi/ebx, 1|ms  (bf/be/bb imm32) -- the timeout register pushed first
            for k in re.finditer(rb'[\xbb\xbe\xbf](\x01|' + re.escape(bytes([ms])) + rb')\x00\x00\x00', win):
                p = m.start() - 0x60 + k.start() + 1
                done.append(p)
                if not dry: b[p] = ms
            if not done:
                # Not inlined: the wait function takes the timeout in ecx. Patch callers `mov ecx,1; call <it>`.
                # (it may be wrapped by an outer function taking ecx the same way: also take the function one level up)
                fs = b.rfind(b'\xcc\xcc', 0, m.start()) + 2   # function starts after the int3 padding
                calls = lambda t: [c.start() for c in re.finditer(rb'\xe8', b)
                                   if c.start() + 5 <= len(b) and c.start() + 5 + struct.unpack_from('<i', b, c.start() + 1)[0] == t]
                targets = {fs} | {b.rfind(b'\xcc\xcc', 0, c) + 2 for c in calls(fs)}
                # `mov ecx,1` up to 0x20 bytes before the call (one DBServer caller interleaves a cmov),
                # as long as nothing in between rewrites ecx (mov ecx,r/m / xor ecx,ecx / another mov ecx,imm).
                for t in targets:
                    for c in calls(t):
                        w = b[c - 0x20:c]
                        k = max(w.rfind(b'\xb9\x01\x00\x00\x00'), w.rfind(b'\xb9' + bytes([ms]) + b'\x00\x00\x00'))
                        if k < 0 or re.search(rb'\xb9|\x8b[\x0d\x4d\xc8-\xcf]|\x33\xc9', w[k + 5:]): continue
                        done.append(c - 0x20 + k + 1)
                        if not dry: b[c - 0x20 + k + 1] = ms
    # The loops' real pacer is Sleep(1) in its idle path, ~0.5 ms under Wine. Sleep(1) -> Sleep(SLEEP_MS) in
    # back-end servers; MapServer keeps it (game tick timing).
    sl = iat.get(b'Sleep')
    if sl and not os.path.basename(f).lower().startswith('mapserver'):
        for k in re.finditer(rb'\x6a(\x01|' + re.escape(bytes([sleep_ms])) + rb')\xff\x15' + re.escape(struct.pack('<I', sl)), b):
            done.append(k.start() + 1)
            if not dry: b[k.start() + 1] = sleep_ms
    # Main loops also poll _kbhit() for debug hotkeys: a conhost round-trip per tick under Wine.
    # Rebind the import to _rmtmp (same DLL, same length, int(void), returns 0, no syscalls).
    k = b.find(b'\x00_kbhit\x00')
    if k > 0:
        done.append('kbhit')
        if not dry: b[k + 1:k + 7] = b'_rmtmp'
    print(f'{os.path.basename(f)}: {len(done)} site(s) {[x if isinstance(x, str) else hex(x) for x in done]}')
    if done and not dry: open(f, 'wb').write(b)

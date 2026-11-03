# -*- coding: utf-8 -*-
r"""Check of the one-template lower bound (2026-10-31): for 2 <= a < b, gcd = 1,
   M = b(b^2+b+a+1), A = {a u' + b u : 1 <= u, u' <= b}, m' = min{m in A : a m > M},
   n = min(a m', M+ab+1) - 1, colouring
   C0 = {x <= ab-1, a!|x} U {a^2 u : u <= b} U [M+1, n],  C1 = {a|x, x <= ab(b+1)} minus C0,  C2 = the rest.
Counts monochromatic solutions of a(x-y) = bz in [1,n] (must be 0).  Run: python tools\check_hybrid2.py BMAX"""
import sys, numpy as np
from math import gcd
B = int(sys.argv[1]) if len(sys.argv) > 1 else 30
B0 = int(sys.argv[2]) if len(sys.argv) > 2 else 3
bad = 0; cnt = 0
for b in range(B0, B + 1):
    for a in range(2, b):
        if gcd(a, b) != 1: continue
        M = b * (b * b + b + a + 1)
        A = {a * up + b * u for u in range(1, b + 1) for up in range(1, b + 1)}
        mp_ = [m for m in A if a * m > M]
        n = min([a * min(mp_)] if mp_ else [] + [M + a * b + 1])
        n = min(n, M + a * b + 1) - 1
        x = np.arange(n + 1); col = np.full(n + 1, 2, dtype=np.int8)
        nm = x % a != 0
        col[(x % a == 0) & (x <= a * b * (b + 1))] = 1
        col[nm & (x <= a * b - 1)] = 0
        col[[a * a * u for u in range(1, b + 1)]] = 0
        col[M + 1:] = 0
        mono = 0; s = 1
        while a * s <= n and b * s < n:
            z = a * s; d = b * s
            y = np.arange(1, n - d + 1)
            mono += int(np.sum((col[y] == col[y + d]) & (col[y] == col[z])))
            s += 1
        cnt += 1
        if mono: bad += 1; print("VIOLATION", a, b, n, mono)
print(f"cells {cnt}, violations {bad} (b <= {B})")

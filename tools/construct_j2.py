# -*- coding: utf-8 -*-
r"""Explicit 3-colouring of [1, n], n = b^3+2b^2-17, for a(x-y)=bz with a = b-2 (b odd), found 2026-10-28 by MaxSAT
(tools\structure_search.py: 0 exceptions for b = 17..25).  v = a-adic valuation.
  v = 0 (a does not divide x): colour 0 if x <= ab-1 or x >= n-2b, else colour 2
  v = 1 (x = a*m):             colour 1 if m <= b(b+1),        else colour 2
  v >= 2:                       colour 0 if x/a^2 <= b, colour 1 if b < x/a^2 <= b+3, else colour 2
Checks every solution (x>y, z <= n).  0 monochromatic solutions for a value of b => R3((b-2)(x-y)=bz) >= b^3+2b^2-16.
Run: python tools\construct_j2.py 17 19 21 ... (default 17..61 odd)"""
import sys
import numpy as np


def va(x, a):
    e = 0
    while x % a == 0:
        x //= a; e += 1
    return e


def colouring(b, n=None):
    a = b - 2
    n = n or b ** 3 + 2 * b * b - 17
    col = np.zeros(n + 1, dtype=np.int8)
    for x in range(1, n + 1):
        t = va(x, a)
        if t == 0:
            col[x] = 0 if (x <= a * b - 1 or x >= n - 2 * b) else 2
        elif t == 1:
            col[x] = 1 if x // a <= b * (b + 1) else 2
        else:
            q = x // (a * a)
            col[x] = 0 if q <= b else (1 if q <= b + 3 else 2)
    return a, n, col


def bad_count(a, b, n, col):
    import math
    g = math.gcd(a, b); da = b // g; za = a // g
    bad = 0; s = 1
    while da * s <= n - 1 and za * s <= n:
        d = da * s; z = za * s
        y = np.arange(1, n - d + 1)
        bad += int(((col[y] == col[y + d]) & (col[y] == col[z])).sum())
        s += 1
    return bad


if __name__ == "__main__":
    bs = [int(x) for x in sys.argv[1:]] or list(range(17, 63, 2))
    for b in bs:
        a, n, col = colouring(b)
        print(f"b={b} a={a} n={n}: monochromatic solutions = {bad_count(a, b, n, col)}", flush=True)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent check of all lower bounds used in the two papers (written 2026-11-03, separate from the search programs).

A k-colouring C of [1,n] is GOOD for a(x-y)=bz (gcd(a,b)=1) if no solution has x, y, z of one colour.
Every solution is z = a*s, x - y = b*s (s >= 1), so we simply loop over s and y.  (Plain loops over numpy arrays.)

Checked here:
  1. every certificate results/lower_bounds/*.json  (keys a, b, k, n, coloring = list of n colours for 1..n)
  2. paper 1, Theorem 1.2: the explicit 3-colouring of [N(a,b)-1], all coprime 2 <= a < b <= BMAX3 (default 34)
  3. paper 1, Lemma 4.1: the recursive colourings T_k for the pairs and k used in the papers
  4. paper 2, Theorem 3.1: the colouring of [a^k+a^(k-1)-2a] for a(x-y)=(a-1)z, 2 <= a <= 7, 2 <= k <= 5 (n <= 20000)
Usage:  python3 tools/check_lower_bounds.py [BMAX3]
Expected last line:  ALL GOOD
"""
import glob, json, os, sys
from math import gcd
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def bad_solutions(a, b, col):
    """number of monochromatic solutions; col[0] is unused, col[1..n] are the colours"""
    col = np.asarray(col, dtype=np.int64)
    n = len(col) - 1
    bad, s = 0, 1
    while a * s <= n and b * s < n:
        z, d = a * s, b * s
        y = col[1:n - d + 1]
        x = col[1 + d:n + 1]
        bad += int(np.count_nonzero((y == col[z]) & (x == col[z])))
        s += 1
    return bad


def N3(a, b):
    """N(a,b) = min(a*m', M+ab+1) of paper 1"""
    M = b * (b * b + b + a + 1)
    A = {a * u2 + b * u for u in range(1, b + 1) for u2 in range(1, b + 1)}
    return min([a * m for m in A if a * m > M] + [M + a * b + 1])


def lower3(a, b):
    """the colouring of paper 1, Theorem 1.2, on [1, N-1]"""
    n = N3(a, b) - 1
    M = b * (b * b + b + a + 1)
    Q2 = {a * a * u for u in range(1, b + 1)}
    col = [None] * (n + 1)
    for x in range(1, n + 1):
        if (x <= a * b - 1 and x % a) or x in Q2 or x > M:
            col[x] = 0
        elif x % a == 0 and x <= a * b * (b + 1):
            col[x] = 1
        else:
            col[x] = 2
    col[0] = -1
    return col


def T(a, b, k):
    """the recursive colouring T_k of paper 1, Section 4 (no check of (I2) here: the colouring itself is checked)"""
    L = b * b + b + 1
    col = [-1] + [1 if (m % a == 0 and m // a <= b) else 0 for m in range(1, L)]      # T_2 on [1, L-1]
    for kk in range(3, k + 1):
        M = b * (L + a)
        n = b * (L + 2 * a)
        sig = lambda c: 1 if c == 0 else (0 if c == 1 else c)
        new = [-1] * (n + 1)
        for x in range(1, n + 1):
            if x > M:
                new[x] = 0
            elif x % a:
                new[x] = 0 if x <= a * b - 1 else kk - 1
            else:
                m = x // a
                new[x] = sig(col[m]) if m <= L - 1 else kk - 1
        col, L = new, n + 1
    return col


def H3(a, k):
    """the colouring of paper 2, Theorem 3.1, for a(x-y)=(a-1)z on [1, a^k+a^(k-1)-2a]"""
    n = a ** k + a ** (k - 1) - 2 * a
    col = [-1] * (n + 1)
    for j in range(2, k + 1):
        for lo, hi in ((a ** (j - 1) - a + 1, a ** j - a), (n - a ** j + a + 1, n - a ** (j - 1) + a)):
            for x in range(lo, hi + 1):
                col[x] = j
    for x in range(1, n + 1):
        v, y = 0, x
        while y % a == 0:
            y //= a; v += 1
        if v >= 1:
            col[x] = v
    assert min(col[1:]) >= 1 and max(col[1:]) <= k, (a, k)
    return col


def main():
    bmax3 = int(sys.argv[1]) if len(sys.argv) > 1 else 34
    fails = 0

    print("1. certificates in results/lower_bounds/")
    for f in sorted(glob.glob(os.path.join(ROOT, "results", "lower_bounds", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        a, b, k, n, c = d["a"], d["b"], d["k"], d["n"], d["coloring"]
        ok = len(c) == n and len(set(c)) <= k
        bad = bad_solutions(a, b, [-1] + list(c))
        print(f"   {os.path.basename(f)}: a={a} b={b} k={k} n={n} colours={len(set(c))} monochromatic={bad} "
              f"-> R_{k} >= {n + 1} {'OK' if ok and bad == 0 else 'FAIL'}")
        fails += not (ok and bad == 0)

    print(f"2. paper 1, Theorem 1.2 (3 colours, [N-1]), all coprime 2 <= a < b <= {bmax3}")
    cnt = 0
    for b in range(3, bmax3 + 1):
        for a in range(2, b):
            if gcd(a, b) != 1:
                continue
            col = lower3(a, b)
            bad = bad_solutions(a, b, col)
            cnt += 1
            if bad:
                print(f"   FAIL ({a},{b}): {bad}"); fails += 1
    print(f"   {cnt} pairs checked")

    print("3. paper 1, recursive colourings T_k (Lemma 4.1)")
    for a, b, k in [(3, 4, 4), (3, 4, 5), (3, 5, 4), (3, 5, 5), (4, 7, 4), (5, 8, 4), (5, 8, 5)]:
        col = T(a, b, k)
        bad = bad_solutions(a, b, col)
        print(f"   T_{k} for ({a},{b}) on [1,{len(col) - 1}]: monochromatic={bad} -> R_{k} >= {len(col)} {'OK' if bad == 0 else 'FAIL'}")
        fails += bad != 0

    print("4. paper 2, Theorem 3.1 (a(x-y)=(a-1)z)")
    for a in range(2, 8):
        for k in range(2, 6):
            n = a ** k + a ** (k - 1) - 2 * a
            if n > 20000:
                continue
            bad = bad_solutions(a, a - 1, H3(a, k))
            if bad:
                print(f"   FAIL a={a} k={k}: {bad}"); fails += 1
    print("   2 <= a <= 7, 2 <= k <= 5, n <= 20000 checked")

    print("ALL GOOD" if fails == 0 else f"{fails} FAILURES")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()

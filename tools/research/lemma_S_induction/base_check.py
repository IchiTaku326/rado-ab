#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base case of the "lower part" of Conjecture S (paper 1, Section 7.3, item (i)), 2026-11-03.
For every main-region pair (a,b) with BMIN <= b <= BMAX, in the chain-and-copy system of lower_table2.py (chain positions
0..T-1, T = b^2+b+1+2a, copy a*[1,b^2+b+1]), ask whether phi on [1,a] can differ from the pattern c1,...,c1,c0:
  test 1: phi(a) = colour 0 and some m < a has colour 0                      (SAT = base fails)
  test 2: phi(a) = 0, phi(1) = 1, no m < a has colour 0, some m in [2,a-1] has colour 2   (only for a > 2)
UNSAT in both tests = the base case holds.  Expected: SAT only for (2,3) and (2,5).
Usage (from the repository root):  python3 tools/research/lemma_S_induction/base_check.py 3 30 [path/to/cadical]
"""
import os, sys, time, tempfile
from math import gcd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lower_table2 as L

bmin, bmax = int(sys.argv[1]), int(sys.argv[2])
cad = sys.argv[3] if len(sys.argv) > 3 else os.path.join("bin_linux", "cadical")
L.G["cad"] = os.path.abspath(cad)
L.G["tmp"] = tempfile.gettempdir()
print("a b test1 test2 seconds", flush=True)
for b in range(bmin, bmax + 1):
    for a in range(2, b):
        if gcd(a, b) != 1 or a * a + (b - 1) * a > b * b + b + 1:
            continue
        R2, T, K0 = L.cell_params(a, b)
        nE, copy, chain, sols = L.build(a, b, T)
        allk = set(range(nE)); t = time.time()
        f1 = lambda v: [[v(copy[a], 0)], [v(copy[m], 0) for m in range(1, a)]]
        r1 = L.solve(nE, sols, f1, allk)
        if a > 2:
            f2 = lambda v: ([[v(copy[a], 0)], [v(copy[1], 1)]] + [[-v(copy[m], 0)] for m in range(1, a)]
                            + [[v(copy[m], 2) for m in range(2, a)]])
            r2 = L.solve(nE, sols, f2, allk)
        else:
            r2 = "n/a"
        print(a, b, r1, r2, "%.1fs" % (time.time() - t), flush=True)

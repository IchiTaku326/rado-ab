# -*- coding: utf-8 -*-
r"""(I2) exact check with arithmetic-progression pieces (2026-11-02 JST, replaces the array method of tools/i2_scan.py; no big arrays).
Recursion: C0_k = N_ab ∪ (M_k, L_k-1] ∪ a*C1_(k-1),  C1_k = a*C0_(k-1),  N_ab = {x < ab : a ∤ x}.
(I2)_k: no m, s in C1_(k-1) with M_k < a m + b s <= M_k + ab.  Result: (I2)_k for all k<=K  <=>  D<=1 or a+1<=D<=2a  (D = a^2+ab-b^2).
Run: python tools\research\i2_sym_scan.py 120 20   (b<=120, k<=20; ~1 min, results\i2_sym.csv)"""
import sys, csv, os, time
from math import gcd
from multiprocessing import Pool
def aps_N(a, top):
    return [(r, a, (top - r) // a + 1) for r in range(1, a) if r <= top]
def run(a, b, K):
    L = {2: b * b + b + 1}
    for k in range(3, K + 1): L[k] = b * (L[k - 1] + 2 * a) + 1
    top = b * b + b
    C1 = [(a, a, b)]
    C0 = aps_N(a, top) + ([(a * (b + 1), a, top // a - b)] if top // a > b else [])
    res = {}
    for k in range(3, K + 1):
        Lp = L[k - 1]; M = b * (Lp + a); n = M + a * b; bad = None
        rng = [(p, p[0], p[0] + p[1] * (p[2] - 1)) for p in C1 if p[2] > 0]
        for P, pmin, pmax in rng:
            for Q, qmin, qmax in rng:
                if a * pmax + b * qmax <= M or a * pmin + b * qmin > n: continue
                (X, xa), (Y, ya) = ((P, a), (Q, b)) if P[2] <= Q[2] else ((Q, b), (P, a))
                y0, dy, cy = Y
                for i in range(X[2]):
                    x = X[0] + X[1] * i; lo = M - xa * x; hi = n - xa * x
                    jl = max((lo - ya * y0) // (ya * dy) + 1, 0); jh = min((hi - ya * y0) // (ya * dy), cy - 1)
                    if jl <= jh:
                        y = y0 + dy * jl; bad = (x, y) if xa == a else (y, x); break
                if bad: break
            if bad: break
        res[k] = bad
        if bad: break
        C0, C1 = aps_N(a, a * b - 1) + [(M + 1, 1, L[k] - 1 - M)] + [(a * s, a * d, c) for s, d, c in C1], [(a * s, a * d, c) for s, d, c in C0]
    return res
def f(arg):
    a, b, K = arg; r = run(a, b, K); ff = next((k for k, v in r.items() if v), "")
    return a, b, int(a * a + a * b <= b * b), a * a + a * b - b * b, ff, r.get(ff, "") if ff else ""
if __name__ == "__main__":
    B, K = int(sys.argv[1]), int(sys.argv[2])
    jobs = [(a, b, K) for b in range(3, B + 1) for a in range(2, b) if gcd(a, b) == 1 and a * a + (b - 1) * a <= b * b + b + 1]
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "i2_sym.csv")
    t = time.time(); bad = 0
    with Pool(11) as p: R = p.map(f, jobs, chunksize=4)
    w = csv.writer(open(out, "w", newline="")); w.writerow(["a", "b", "golden", "D", "first_fail_k", "witness_m_s"])
    for a, b, g, D, ff, wt in R:
        w.writerow([a, b, g, D, ff, wt]); pred = "" if (D <= 1 or a + 1 <= D <= 2 * a) else (4 if D >= 2 * a + 1 else 5)
        bad += str(pred) != str(ff)
    print(f"{len(jobs)} cells, k<={K}, mismatches with the D criterion: {bad}, {time.time()-t:.0f}s -> {out}")

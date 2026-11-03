# -*- coding: utf-8 -*-
r"""Rigorous check (by SAT, with assumptions) of 'forced equalities' in valid k-colourings of [1, a^k - 1]:
for the numbers with v_a(x)=j (a-adic valuation) is it IMPOSSIBLE that two of them have different colours?
For each level j, rep = smallest number of the level, and for each other x of the level: for every ordered colour pair
(c, c') with c != c': SAT( chi(rep)=c and chi(x)=c' ) must be UNSAT (no symmetry breaking in these queries).
Also: for pairs of levels (j,j'): is 'chi(rep_j) != chi(rep_j')' forced?
Output: results\forced.txt (JST).  Usage: python tools\forced.py  (cells a,b,k separated by ;)
"""
import argparse, os, sys, time
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rado_c1 import build_cnf
JST = timezone(timedelta(hours=9))
def now(): return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
def val(a, x):
    e = 0
    while x % a == 0: x //= a; e += 1
    return e
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cells", default="3,1,2;5,2,2;3,1,3;4,1,3;5,2,3;5,3,3;7,5,3;3,1,4;4,1,4")
    args = ap.parse_args()
    from pysat.solvers import Glucose4
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "forced.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    def log(s):
        print(s, flush=True)
        with open(out, "a", encoding="utf-8") as f: f.write(s + "\n"); f.flush(); os.fsync(f.fileno())
    for t in args.cells.split(";"):
        a, b, k = (int(x) for x in t.split(","))
        n = a ** k - 1; t0 = time.time()
        cl, nv, v = build_cnf(a, b, k, n, symbreak=False)
        S = Glucose4(bootstrap_with=cl)
        def can_differ(x, y):
            for c in range(k):
                for c2 in range(k):
                    if c != c2 and S.solve(assumptions=[v(x, c), v(y, c2)]): return True
            return False
        levels = {}
        for x in range(1, n + 1): levels.setdefault(val(a, x), []).append(x)
        if not S.solve():
            log(f"[{now()} JST] ({a},{b},{k}) n={n}: UNSAT already (no colouring)"); S.delete(); continue
        res = []
        for j in sorted(levels):
            xs = levels[j]; rep = xs[0]; bad = [x for x in xs[1:] if can_differ(rep, x)]
            res.append(f"v={j}: {len(xs)} numbers, uniform FORCED={not bad}" + (f" (can differ: {bad[:5]})" if bad else ""))
        reps = {j: levels[j][0] for j in levels}
        diff = [f"{i}!={j}:{'forced' if not any(S.solve(assumptions=[v(reps[i], c), v(reps[j], c)]) for c in range(k)) else 'free'}" for i in sorted(reps) for j in sorted(reps) if i < j]
        log(f"[{now()} JST] (a,b,k)=({a},{b},{k}) n={n} ({time.time()-t0:.0f}s):")
        for r in res: log("    " + r)
        log("    level reps different? " + ", ".join(diff))
        S.delete()
if __name__ == "__main__":
    main()

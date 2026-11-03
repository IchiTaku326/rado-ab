# -*- coding: utf-8 -*-
r"""Collect extremal 3-colourings for the cells where conjecture C is an equality: n = R-1 (the largest colourable n).
Solved with pysat MiniSat (minisat22) streaming, checked against ALL solutions by an independent loop, saved as
results\colorings\a{a}_b{b}_k3_n{n}.json.  Finished files are skipped on restart (Ctrl+C is safe).  One cell at a time
(optional arguments: cells as a,b,R ...)
(memory: about 1-3 GB up to b=31).  Run: python tools\collect_colorings.py   (then: python tools\analyze_colorings.py)"""
import json, os, sys, time
from datetime import datetime, timezone, timedelta
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
JST = timezone(timedelta(hours=9))
OUT = os.path.join(HERE, "..", "results", "colorings")
# (a, b, R): conjecture C equality cells (R = b^3+2b^2-j^2(j+2)), j = 2, 3, 4 ; plus a few cells outside it for comparison
CELLS = [(15, 17, 5475), (17, 19, 7565), (19, 21, 10127), (21, 23, 13209), (23, 25, 16859), (25, 27, 21125), (27, 29, 26055), (29, 31, 31697),
         (20, 23, 13180), (22, 25, 16830), (23, 26, 18883), (25, 28, 23475), (26, 29, 26026), (28, 31, 31668),
         (29, 33, 38019)]


def solve(a, b, n, k=3):
    from pysat.solvers import Solver
    from rado_c1 import iter_cnf
    v = lambda j, c: (j - 1) * k + c + 1
    with Solver(name="minisat22") as S:
        for c in iter_cnf(a, b, k, n):
            S.add_clause(c)
        if not S.solve():
            return None
        pos = set(l for l in S.get_model() if l > 0)
    return [next(c for c in range(k) if v(j, c) in pos) for j in range(1, n + 1)]


def check(a, b, col):
    """independent check: every x>y, z in [1,n] with a(x-y)=bz must not be monochromatic"""
    n = len(col); bad = 0
    for z in range(1, n + 1):
        if (b * z) % a: continue
        d = b * z // a
        cz = col[z - 1]
        for y in range(1, n - d + 1):
            if col[y - 1] == cz and col[y + d - 1] == cz:
                bad += 1
    return bad


def main():
    os.makedirs(OUT, exist_ok=True)
    cells = [tuple(map(int, t.split(","))) for t in sys.argv[1:]] or CELLS    # optional: a,b,R a,b,R ...
    for a, b, R in cells:
        n = R - 1
        path = os.path.join(OUT, f"a{a}_b{b}_k3_n{n}.json")
        if os.path.exists(path):
            continue
        t = time.time()
        print(f"[{datetime.now(JST):%Y-%m-%d %H:%M:%S} JST] ({a},{b}) n={n} ...", flush=True)
        col = solve(a, b, n)
        if col is None:
            print("   UNSAT?? (should be SAT) - skipped", flush=True); continue
        bad = check(a, b, col)
        print(f"   SAT in {time.time() - t:.0f}s, check: {bad} monochromatic solutions", flush=True)
        if bad: continue
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"a": a, "b": b, "k": 3, "n": n, "R": R, "solver": "minisat22",
                       "jst_time": f"{datetime.now(JST):%Y-%m-%d %H:%M:%S}", "coloring": col}, f)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
r"""Lemma F' check (2026-11-02, upper-bound proof, formula-1 region): one position short of the limit (chain 1+bt, t <= R2+2a-1,
copy a*m, m <= R2; only copy-internal solutions and chain-chain solutions with z = a*(u-t) in the copy), every good 3-colouring
gives the 10 copy numbers a*{a, 2a, R2, m, p, p-a, p-2a, R2-p, R2+a-p, R2+2a-p} the 'template pattern' (a, 2a one colour,
R2 a second colour, the other 7 the third colour).  Together with Lemma W (hand proof) this gives R3 <= N = b(R2+2a)+1.
Per cell: base formula must be SAT (sanity) and 'base + pattern violated' must be UNSAT.  11 processes, MiniSat (pysat),
results\forced_F.csv (one row per cell, resumable), ETA.   Run: python tools\forced_F.py --workers 11 --bmax 30"""
import csv, itertools, os, sys, time
from math import gcd
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "forced_F.csv")


def phi_t(a, b, m):
    if m % a == 0 and m // a <= b: return 0
    return 1 if m <= b * (b + 1) else 2


def good_p(a, b):
    R2 = b * b + b + 1
    for p in range(2 * a + 1, R2):
        x = 1 + b * p
        if x % a: continue
        m = x // a
        if m > R2 or phi_t(a, b, m) != 1: continue
        if all(1 <= d <= b * (b + 1) and phi_t(a, b, d) == 1 for d in (p, p - a, p - 2 * a, R2 - p, R2 + a - p, R2 + 2 * a - p)): return p
    return None


def cell(ab):
    a, b = ab; t0 = time.time()
    from pysat.solvers import Solver
    R2 = b * b + b + 1; T = R2 + 2 * a - 1
    p = good_p(a, b)
    if p is None: return a, b, "", "NO_P", "", round(time.time() - t0, 1)
    S = sorted(set(a * m for m in range(1, R2 + 1)) | set(1 + b * t for t in range(T + 1)))
    idx = {x: i for i, x in enumerate(S)}; v = lambda x, c: 3 * idx[x] + c + 1; C = set(1 + b * t for t in range(T + 1))
    s = Solver(name="minisat22")
    for x in S: s.add_clause([v(x, 0), v(x, 1), v(x, 2)])
    s.add_clause([v(a, 0)])
    for Z in range(a, R2 + 1, a):
        d = b * Z // a
        for Y in range(1, R2 + 1):
            X = Y + d
            if X > R2: break
            Tt = sorted({a * X, a * Y, a * Z})
            for c in range(3): s.add_clause([-v(t, c) for t in Tt])
    Cl = sorted(C)
    for i, x in enumerate(Cl):
        for y in Cl[i + 1:]:
            sd = (y - x) // b
            if sd > R2: break
            Tt = sorted({x, y, a * sd})
            for c in range(3): s.add_clause([-v(t, c) for t in Tt])
    base = s.solve()
    m = (1 + b * p) // a
    g0, g2, g1 = [a, 2 * a], [R2], [m, p, p - a, p - 2 * a, R2 - p, R2 + a - p, R2 + 2 * a - p]
    for X, Y, Z in itertools.permutations(range(3)):
        s.add_clause([-v(a * e, X) for e in g0] + [-v(a * e, Y) for e in g2] + [-v(a * e, Z) for e in g1])
    viol = s.solve(); s.delete()
    return a, b, p, ("SAT" if base else "UNSAT"), ("SAT" if viol else "UNSAT"), round(time.time() - t0, 1)


def main():
    args = sys.argv[1:]; W, B = 11, 30
    while args:
        if args[0] == "--workers": W = int(args[1])
        elif args[0] == "--bmax": B = int(args[1])
        args = args[2:]
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["a"]), int(r["b"])))
    cells = [(a, b) for b in range(4, B + 1) for a in range(2, b) if gcd(a, b) == 1 and a * a + (b - 1) * a <= b * b + b + 1 and (a, b) not in done]
    new = not os.path.exists(OUT); fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "p", "base_T_minus_1", "pattern_violated", "seconds"]); fh.flush()
    print(f"{len(cells)} cells ({len(done)} done), {W} processes", flush=True)
    t0 = time.time(); wt = sum(b ** 4 for a, b in cells); wd = 0; bad = 0
    with mp.Pool(W) as pool:
        for i, r in enumerate(pool.imap_unordered(cell, cells), 1):
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), *r]); fh.flush(); os.fsync(fh.fileno())
            wd += r[1] ** 4; el = time.time() - t0; bad += not (r[3] == "SAT" and r[4] == "UNSAT")
            print(f"[{datetime.now(JST):%H:%M:%S}] {i}/{len(cells)} ({r[0]},{r[1]}) p={r[2]} base {r[3]} violated {r[4]} {r[5]}s | not as expected {bad} | ETA about {el/max(wd,1)*(wt-wd)/60:.0f} min", flush=True)
    print("done (results\\forced_F.csv)")


if __name__ == "__main__":
    mp.freeze_support(); main()

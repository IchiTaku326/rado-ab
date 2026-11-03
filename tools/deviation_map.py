# -*- coding: utf-8 -*-
r"""Lemma S research (2026-11-02): reduced 3-colour problem of the formula-1 upper bound (copy a*m, m <= R2 = b^2+b+1, with its own
solutions; chain 1+b*t, t < L, with chain-chain solutions z = a*(u-t) in the copy).  For chain length L = R2+2a-j (j = 0..2a) and
every copy element m, can colour(a*m) differ from the template class representative (a*a for m = a*u, u <= b; a*R2 for m = R2; a for
the others)?  Observed in the cloud: for 1 <= j <= a exactly the top j elements m = b(b+1)-j+1 .. b(b+1) can deviate; j = 0 none
(= Lemma S).  MiniSat (pysat) incremental with assumptions, 11 processes, results\deviation_map.csv, resumable, ETA.
Run: python tools\deviation_map.py --workers 11 --bmax 15"""
import csv, os, sys, time
from math import gcd
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "deviation_map.csv")


def cell(arg):
    a, b, j = arg; t0 = time.time()
    from pysat.solvers import Solver
    R2 = b * b + b + 1; L = R2 + 2 * a - j
    num = {}
    for m in range(1, R2 + 1): num.setdefault(a * m, len(num))
    for t in range(L): num.setdefault(1 + b * t, len(num))
    v = lambda x, c: 3 * num[x] + c + 1
    s = Solver(name="minisat22")
    for x in num:
        s.add_clause([v(x, 0), v(x, 1), v(x, 2)])
        s.add_clause([-v(x, 0), -v(x, 1)]); s.add_clause([-v(x, 0), -v(x, 2)]); s.add_clause([-v(x, 1), -v(x, 2)])
    s.add_clause([v(a, 0)])
    for Z in range(a, R2 + 1, a):
        d = b * Z // a
        for Y in range(1, R2 + 1):
            X = Y + d
            if X > R2: break
            T3 = sorted({a * X, a * Y, a * Z})
            for c in range(3): s.add_clause([-v(t, c) for t in T3])
    for t in range(L):
        for u in range(t + 1, L):
            sd = u - t
            if sd > R2: break
            T3 = sorted({1 + b * t, 1 + b * u, a * sd})
            for c in range(3): s.add_clause([-v(q, c) for q in T3])
    base = s.solve()
    devs = []
    if base:
        for m in range(1, R2 + 1):
            r = a * a if (m % a == 0 and m // a <= b) else (a * R2 if m == R2 else a)
            if r == a * m: continue
            if any(s.solve(assumptions=[v(a * m, c1), v(r, c2)]) for c1 in range(3) for c2 in range(3) if c1 != c2): devs.append(m)
    s.delete()
    return a, b, j, L, ("SAT" if base else "UNSAT"), " ".join(map(str, devs)), round(time.time() - t0, 1)


def main():
    args = sys.argv[1:]; W, B = 11, 15
    while args:
        if args[0] == "--workers": W = int(args[1])
        elif args[0] == "--bmax": B = int(args[1])
        args = args[2:]
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["a"]), int(r["b"]), int(r["j"])))
    jobs = [(a, b, j) for b in range(4, B + 1) for a in range(2, b) if gcd(a, b) == 1 and a * a + (b - 1) * a <= b * b + b + 1
            for j in range(0, 2 * a + 1) if (a, b, j) not in done]
    new = not os.path.exists(OUT); fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "j", "L", "base", "deviating_m", "seconds"]); fh.flush()
    print(f"{len(jobs)} jobs ({len(done)} done), {W} processes", flush=True)
    t0 = time.time(); wt = sum(b ** 5 for a, b, j in jobs); wd = 0
    with mp.Pool(W) as pool:
        for i, r in enumerate(pool.imap_unordered(cell, jobs), 1):
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), *r]); fh.flush(); os.fsync(fh.fileno())
            wd += r[1] ** 5; el = time.time() - t0
            print(f"[{datetime.now(JST):%H:%M:%S}] {i}/{len(jobs)} ({r[0]},{r[1]}) j={r[2]} {r[4]} devs=[{r[5][:60]}] {r[6]}s | ETA about {el/max(wd,1)*(wt-wd)/60:.0f} min", flush=True)
    print("done (results\\deviation_map.csv)")


if __name__ == "__main__":
    mp.freeze_support(); main()

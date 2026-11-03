# -*- coding: utf-8 -*-
r"""Step toward the UPPER-BOUND proof (task 2): in every valid 3-colouring of the small set S at the LIMIT n = R-1
(S = {a*m : m <= K} U {x = n (mod b)}, K = b^2+b+1), which multiples a*m are FORCED to have the same colour as a (= a*1)
or as a^2, which are forced to be different, and which are free?  (Found on (7,9): a*m with a not dividing m, m <= 85, all
the same colour as a; a^2*u (u <= b) all different; only m = 86..90 free.)
For each cell (all known exact values with 5 <= b <= --bmax, 2 <= a < b): incremental MiniSat with assumptions
(no symmetry clauses; "ref has colour 0" is w.l.o.g.).  One row per cell in results\forced_survey.csv: the m's as ranges.
11 processes, Ctrl+C safe, rows of finished cells are skipped on restart, ETA.
Run: python tools\forced_survey.py 30"""
import csv, os, sys, time
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
JST = timezone(timedelta(hours=9))
MODE = os.environ.get("FORCED_MODE", "full")        # full: S as before / copy: only the multiples a*[1,K] (no residue chain)
SHIFT = int(os.environ.get("FORCED_SHIFT", "0"))
FRAC = float(os.environ.get("FORCED_FRAC", "0"))   # if > 0: n = floor(FRAC * R) (how far down does the forcing reach?)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results",
                   "forced_survey.csv" if (MODE == "full" and SHIFT == 0 and FRAC == 0) else (f"forced_survey_{MODE}_f{FRAC:g}.csv" if FRAC > 0 else f"forced_survey_{MODE}_s{SHIFT}.csv"))


def ranges(xs):
    xs = sorted(xs); out = []
    for x in xs:
        if out and x == out[-1][1] + 1: out[-1][1] = x
        else: out.append([x, x])
    return " ".join(f"{p}" if p == q else f"{p}-{q}" for p, q in out)


def work(cell):
    a, b, R = cell; n = int(FRAC * R) if FRAC > 0 else R - 1 - SHIFT; K = b * b + b + 1; r = n % b
    from pysat.solvers import Solver
    t0 = time.time()
    S = [x for x in range(1, n + 1) if (x % a == 0 and x <= a * K) or (MODE == "full" and x % b == r)]
    idx = {x: i for i, x in enumerate(S)}; v = lambda x, c: 3 * idx[x] + c + 1
    s = Solver(name="minisat22")
    for x in S: s.add_clause([v(x, 0), v(x, 1), v(x, 2)])
    q = 1
    while b * q <= n - 1 and a * q <= n:
        d, z = b * q, a * q
        if z in idx:
            for y in S:
                if y + d > n: break
                if y + d in idx:
                    T = sorted({y, y + d, z})
                    for c in range(3): s.add_clause([-v(t, c) for t in T])
        q += 1
    out = []
    for ref in (a, a * a):
        if ref not in idx: out += ["", "", ""]; continue
        same, diff, free = [], [], []
        for m in range(1, K + 1):
            x = a * m
            if x > n or x == ref: continue
            cs = s.solve(assumptions=[v(ref, 0), v(x, 0)]); cd = s.solve(assumptions=[v(ref, 0), -v(x, 0)])
            (same if not cd else diff if not cs else free).append(m)
        out += [ranges(same), ranges(diff), ranges(free)]
    s.delete()
    return (a, b, R, K) + tuple(out) + (round(time.time() - t0, 1),)


def main():
    bmax = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"mode {MODE}, " + (f"n = {FRAC:g} * R" if FRAC > 0 else f"n = R - 1 - {SHIFT}") + f", output {OUT}", flush=True)
    from subset_check import known_R
    R = known_R()
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["a"]), int(r["b"])))
    cells = sorted([(a, b, n) for (a, b), n in R.items() if 2 <= a < b and 5 <= b <= bmax and (a, b) not in done], key=lambda t: -t[1])
    print(f"{len(cells)} cells, 11 processes", flush=True)
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "R", "K", "same_as_a", "diff_from_a", "free_vs_a", "same_as_a2", "diff_from_a2", "free_vs_a2", "seconds"])
    t0 = time.time(); wt = {c: float(c[1]) ** 4 for c in cells}; tw = sum(wt.values()) or 1; dw = 0.0
    with mp.Pool(11) as pool:
        for i, row in enumerate(pool.imap_unordered(work, cells), 1):
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")] + list(row)); fh.flush(); os.fsync(fh.fileno())
            dw += wt[(row[0], row[1], row[2])]; el = time.time() - t0
            print(f"[{datetime.now(JST):%H:%M:%S}] {i}/{len(cells)} ({row[0]},{row[1]}) free vs a: {row[6] or '-'} | elapsed {el/60:.0f} min, ETA about {el/dw*(tw-dw)/60:.0f} min", flush=True)
    print("done (results\\forced_survey.csv)")


if __name__ == "__main__":
    main()

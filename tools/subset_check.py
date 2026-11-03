# -*- coding: utf-8 -*-
r"""Subset test (found 2026-10-29): is [1,n] not 3-colourable already on the small set
      S(n) = { x <= n : a | x }  U  { x <= n : x = n (mod b) }      (only solutions with x, y, z all in S)?
If S(n) is not colourable, [1,n] is not colourable (sound: a colouring of [1,n] restricted to S would colour S).
S has about n/a + n/b numbers instead of n -> far less memory/time for the UNSAT side (the upper bound).
For every known exact value R (decisions.csv: n=R-1 SAT, n=R UNSAT) with bmin <= b <= bmax it solves S(R) with MiniSat.
Also --cells a,b,n ... for single cells (e.g. big ones).  Results: results\subset_check.csv (rows already there are skipped;
Ctrl+C is safe).  Run: python tools\subset_check.py 5 41     or     python tools\subset_check.py --cells 45,49,122310"""
import csv, glob, os, sys, time
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "results", "subset_check.csv")


def known_R():
    R = {}
    for f in glob.glob(os.path.join(HERE, "..", "results", "*", "decisions.csv")):
        st = {}
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            try:
                if r.get("k") != "3": continue
                st.setdefault((int(r["a"]), int(r["b"])), {})[int(r["n"])] = r["status"]
            except Exception:
                pass
        for k, d in st.items():
            uns = [n for n, s in d.items() if s == "UNSAT"]
            if uns and d.get(min(uns) - 1) == "SAT":
                R[k] = min(uns)
    return R


def solve_subset(a, b, n, K=None):
    """K: only the multiples a*m with m <= K (None = all)"""
    from pysat.solvers import Solver
    r = n % b
    S = [x for x in range(1, n + 1) if (x % a == 0 and (K is None or x <= a * K)) or x % b == r]
    idx = {x: i for i, x in enumerate(S)}
    v = lambda x, c: 3 * idx[x] + c + 1
    m = 0
    with Solver(name="minisat22") as so:
        for x in S:
            so.add_clause([v(x, 0), v(x, 1), v(x, 2)])
        so.add_clause([v(S[0], 0)])                       # colour names: the smallest number of S has colour 0
        s = 1
        while b * s <= n - 1 and a * s <= n:
            d, z = b * s, a * s
            if z in idx:
                for y in S:
                    if y + d > n: break
                    if y + d in idx:
                        T = sorted({y, y + d, z})
                        for c in range(3):
                            so.add_clause([-v(t, c) for t in T]); m += 1
            s += 1
        res = so.solve()
    return ("SAT" if res else "UNSAT"), len(S), m


def main():
    global OUT
    args = sys.argv[1:]
    kmode = os.environ.get("SUBSET_K") or None          # also settable by environment (run_parallel)
    if kmode: OUT = os.path.join(HERE, "..", "results", f"subset_K_{kmode}.csv")
    if args and args[0] == "--K":                      # --K bb1 : K = b^2+b+1 (expected UNSAT)   --K bb : K = b^2+b (expected SAT)
        kmode = args[1]; args = args[2:]
        OUT = os.path.join(HERE, "..", "results", f"subset_K_{kmode}.csv")
    if args and args[0] == "--cells":
        cells = [tuple(map(int, t.split(","))) for t in args[1:]]
    else:
        bmin, bmax = int(args[0]), int(args[1]); R = known_R()
        cells = sorted(((a, b, n) for (a, b), n in R.items() if bmin <= b <= bmax and a >= 2), key=lambda t: (t[1], t[0]))
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["a"]), int(r["b"]), int(r["n"])))
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "n", "subset_size", "clauses", "result", "seconds"])
    unsat = sat = 0
    for a, b, n in cells:
        if (a, b, n) in done: continue
        t = time.time(); K = None if kmode is None else (b * b + b + 1 if kmode == "bb1" else b * b + b)
        res, size, m = solve_subset(a, b, n, K)
        w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), a, b, n, size, m, res, round(time.time() - t, 1)])
        fh.flush(); os.fsync(fh.fileno())
        unsat += res == "UNSAT"; sat += res == "SAT"
        print(f"({a},{b}) n={n}: subset {size} numbers, {m} clauses -> {res}  {time.time() - t:.0f}s", flush=True)
    print(f"this run: subset UNSAT {unsat} (= the small set alone proves 'not colourable'), SAT {sat} (small set not enough)")


if __name__ == "__main__":
    main()

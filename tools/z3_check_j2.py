# -*- coding: utf-8 -*-
r"""Independent machine check (Z3, the AutoCase approach of arXiv:2505.12085) of the theorem
   R3((b-2)(x-y)=bz) >= b^3+2b^2-16 for all odd b >= 5   (colouring in tools\construct_j2.py).
For every colour, every choice of "piece" for x, y, z (a piece = valuation type + interval), Z3 must show that
   a(x-y) = bz, 1 <= y < x <= n, 1 <= z <= n, x, y, z in those pieces
has NO integer solution for ANY odd b >= 5 (b symbolic).  Valuation types are written with witnesses:
   v=0: w = a*q + r, 1 <= r <= a-1 | v=1: w = a*m, m = a*q + r, 1 <= r <= a-1 | v>=2: w = a*a*q.
Output: one line per case (unsat = proved, sat = counterexample, unknown = Z3 gave up).  Needs: pip install z3-solver
Run: python tools\z3_check_j2.py"""
import csv, itertools, os, sys, time, multiprocessing as mp
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "z3_check_j2.csv")


CASE_SECONDS = 180


def pieces_def():
    from z3 import Int
    b = Int("b"); a = b - 2; n = b * b * b + 2 * b * b - 17
    return b, a, n, [
        (0, "v0", 1, a * b - 1), (0, "v0", n - 2 * b, n), (0, "v2", 1, b * a * a),
        (1, "v1", 1, a * b * (b + 1)), (1, "v2", b * a * a + 1, (b + 3) * a * a),
        (2, "v0", a * b, n - 2 * b - 1), (2, "v1", a * b * (b + 1) + 1, n), (2, "v2", (b + 3) * a * a + 1, n),
    ]


def one_case(colour, ix, iy, iz, q):
    """runs in its own process (Z3's non-linear solver does not always respect its own timeout)"""
    from z3 import Int, Solver, sat, unsat
    b, a, n, P = pieces_def()
    pieces = [p for p in P if p[0] == colour]
    px, py, pz = pieces[ix], pieces[iy], pieces[iz]
    t = Int("t")
    S = Solver()
    S.add(b == 2 * t + 1, t >= 2)
    x, y, z, s = Int("x"), Int("y"), Int("z"), Int("s")
    S.add(z == a * s, x - y == b * s, s >= 1, y >= 1, x > y, x <= n, z <= n)
    for w, p, nm in ((x, px, "x"), (y, py, "y"), (z, pz, "z")):
        qq, r, m = Int("q" + nm), Int("r" + nm), Int("m" + nm)
        S.add(w >= p[2], w <= p[3])
        if p[1] == "v0": S.add(w == a * qq + r, r >= 1, r <= a - 1)
        elif p[1] == "v1": S.add(w == a * m, m == a * qq + r, r >= 1, r <= a - 1)
        else: S.add(w == a * a * qq)
    res = S.check()
    q.put(("unsat" if res == unsat else ("sat" if res == sat else "unknown"), str(S.model()) if res == sat else ""))


def main():
    """resumable: every finished case is one row in results\\z3_check_j2.csv and is skipped on the next run
    (python tools\\z3_check_j2.py --retry-unknown  tries the 'unknown' cases again)"""
    b, a, n, P = pieces_def()
    total = {"unsat": 0, "sat": 0, "unknown": 0}
    done = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            done[(int(r["colour"]), int(r["ix"]), int(r["iy"]), int(r["iz"]))] = r["result"]
    retry = "--retry-unknown" in sys.argv
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "colour", "ix", "iy", "iz", "case", "result", "seconds", "model"]); fh.flush()
    for colour in range(3):
        pieces = [p for p in P if p[0] == colour]
        k = len(pieces)
        for ix, iy, iz in itertools.product(range(k), repeat=3):
            if pieces[iz][1] == "v0": continue                      # z = a*s is never a unit
            key0 = (colour, ix, iy, iz)
            if key0 in done and not (retry and done[key0] == "unknown"):
                total[done[key0]] += 1; continue
            q = mp.Queue(); pr = mp.Process(target=one_case, args=(colour, ix, iy, iz, q)); t0 = time.time()
            pr.start(); pr.join(CASE_SECONDS)
            if pr.is_alive():
                pr.kill(); pr.join(); key, mdl = "unknown", ""
            else:
                key, mdl = q.get() if not q.empty() else ("unknown", "")
            total[key] += 1
            desc = f"x {pieces[ix][1]}[{ix}], y {pieces[iy][1]}[{iy}], z {pieces[iz][1]}[{iz}]"
            print(f"colour {colour}: {desc} -> {key} ({time.time()-t0:.1f}s){('  model: ' + mdl) if mdl else ''}", flush=True)
            w.writerow([f"{datetime.now(JST):%Y-%m-%d %H:%M:%S}", colour, ix, iy, iz, desc, key, round(time.time() - t0, 1), mdl]); fh.flush(); os.fsync(fh.fileno())
    fh.close()
    print("TOTAL", total)
    print("PROVED (all cases unsat)" if total["sat"] == 0 and total["unknown"] == 0 else "NOT fully proved by Z3 (see sat/unknown lines)")


if __name__ == "__main__":
    main()

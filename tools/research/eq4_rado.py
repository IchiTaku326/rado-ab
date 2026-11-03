# -*- coding: utf-8 -*-
r"""Rado numbers of the 4-variable equation  a(x - y) = b(z + w)  (2026-11-02 JST, question: does a different quadratic
irrational (e.g. the silver ratio 1+sqrt2) take the place of the golden ratio for this equation?)
For every pair 1 <= a, 2 <= b <= BMAX, gcd(a,b) = 1, and k = 2, 3 (in this order), R_k is found by a search on n:
  - monotone (if [1,n] is not colourable, no larger n is), so: start at max(R_(k-1), a lower-bound guess), double the step
    while colourable, then bisect;
  - each test is CaDiCaL (bin_linux\cadical inside WSL) with a time limit; TIMEOUT -> the cell is recorded as unknown;
  - known facts are added as clauses (they only remove symmetric or impossible colourings, results stay exact):
      * the colour of 1 is 0 (symmetry);
      * dilation: d*[1, n//d] is a copy of the problem (homogeneous equation), so if n//d >= R_j (already computed for this
        pair) the copy uses at least j+1 colours: for every set P of j colours, some element of the copy is outside P;
  - every 'colourable' answer gives a colouring that is CHECKED against all solutions (independent routine) before it is used.
Output results\eq4_rado.csv (a, b, k, R or '>n?' if a time limit was hit), resumable; 11 cells in parallel; ETA.
Memory: a test with more than --maxsol solutions (default 3 million) is not run (TOO_BIG), so 11 workers stay below ~17 GB.
Run (inside WSL): python3 tools/research/eq4_rado.py --bmax 12 --kmax 3 --workers 11 --wall 600"""
import argparse, csv, os, subprocess, sys, tempfile, time
from math import gcd
from itertools import combinations
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9)); now = lambda: datetime.now(JST).strftime("%m-%d %H:%M:%S")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
OUT = os.path.join(ROOT, "results", "eq4_rado.csv")
CAD = None

def sols(a, b, n):
    out = set()
    s = 1
    while b * s <= n - 1 and a * s <= 2 * n:
        d, t = b * s, a * s
        for z in range(max(1, t - n), t // 2 + 1):
            w = t - z
            if 1 <= w <= n:
                for y in range(1, n - d + 1):
                    out.add(tuple(sorted({y, y + d, z, w})))
        s += 1
    return out

def check(a, b, n, col):
    for s in range(1, n):
        d, t = b * s, a * s
        if d > n - 1 or t > 2 * n: break
        for z in range(max(1, t - n), t // 2 + 1):
            w = t - z
            if not (1 <= w <= n) or col[z] != col[w]: continue
            c = col[z]
            for y in range(1, n - d + 1):
                if col[y] == c and col[y + d] == c: return False
    return True

def nsols(a, b, n):
    tot = 0; s = 1
    while b * s <= n - 1 and a * s <= 2 * n:
        d, t = b * s, a * s
        zl, zh = max(1, t - n), t // 2
        if zh >= zl: tot += (zh - zl + 1) * (n - d)
        s += 1
    return tot

MAXSOL = 3_000_000      # 9M clauses: CaDiCaL ~1-1.5 GB, so 11 workers fit in WSL's 24 GB; larger tests -> TOO_BIG (--maxsol)

def colourable(a, b, n, k, Rs, wall):
    """v2 (11-02 18:30): clauses are written to the file as they are generated (no big set in memory)"""
    ns = nsols(a, b, n)
    if ns > MAXSOL: return "BIG"
    v = lambda x, c: k * (x - 1) + c + 1
    extra = []
    for x in range(1, n + 1):
        extra.append([v(x, c) for c in range(k)])
        for c in range(k):
            for e in range(c + 1, k): extra.append([-v(x, c), -v(x, e)])
    extra.append([v(1, 0)])
    for d in range(1, n + 1):                                   # dilation copies
        L = n // d; need = max([j for j, R in enumerate(Rs, 1) if isinstance(R, int) and L >= R] + [0])
        if need == 0: break
        D = [d * m for m in range(1, L + 1)]
        for P in combinations(range(k), min(need, k - 1)):
            extra.append([v(x, c) for x in D for c in range(k) if c not in P])
    fd, f = tempfile.mkstemp(suffix=".cnf"); os.close(fd)
    try:
        with open(f, "w") as fh:
            fh.write(f"p cnf {k*n} {len(extra) + k*ns}\n")
            fh.writelines(" ".join(map(str, c)) + " 0\n" for c in extra)
            s_ = 1; cnt = 0
            while b * s_ <= n - 1 and a * s_ <= 2 * n:
                d, t = b * s_, a * s_
                for z in range(max(1, t - n), t // 2 + 1):
                    w = t - z
                    for y in range(1, n - d + 1):
                        T = sorted({y, y + d, z, w}); cnt += 1
                        fh.write("".join(" ".join(str(-v(q, c)) for q in T) + " 0\n" for c in range(k)))
                s_ += 1
            assert cnt == ns
        try:
            out = subprocess.run([CAD, "-q", f], capture_output=True, text=True, timeout=wall).stdout
        except subprocess.TimeoutExpired:
            return None
    finally:
        os.remove(f)
    if "s UNSATISFIABLE" in out: return False
    if "s SATISFIABLE" not in out: return None
    val = set(int(t) for l in out.splitlines() if l.startswith("v") for t in l.split()[1:] if int(t) > 0)
    col = [None] + [next(c for c in range(k) if v(x, c) in val) for x in range(1, n + 1)]
    assert check(a, b, n, col), "colouring check failed"
    return True

def rado(a, b, k, Rs, start, wall):
    """least n such that [1,n] is not k-colourable; None-safe (returns string if a test timed out)"""
    lo = max(1, start)                                            # [1, lo-1] known colourable
    r = colourable(a, b, lo, k, Rs, wall)
    if r == "BIG": return f"TOO_BIG(n={lo})"
    if r is None: return f">{lo-1}?"
    if r is False:                                                # go down (start guess too high)
        hi = lo
        while True:
            lo2 = max(1, hi // 2)
            r = colourable(a, b, lo2, k, Rs, wall)
            if r is None or r == "BIG": return f"<={hi}?"
            if r: lo = lo2 + 1; break
            hi = lo2
            if lo2 == 1: return 1
    else:
        step = max(1, lo // 4); hi = None; lo = lo + 1
        while hi is None:
            r = colourable(a, b, lo + step - 1, k, Rs, wall)
            if r == "BIG":
                if step > 1: step = max(1, step // 4); continue
                return f">{lo-1}?(too big)"
            if r is None: return f">{lo-1}?"
            if r: lo = lo + step; step *= 2
            else: hi = lo + step - 1
    while lo < hi:                                                # [1,lo-1] colourable, [1,hi] not
        mid = (lo + hi) // 2
        r = colourable(a, b, mid, k, Rs, wall)
        if r is None or r == "BIG": return f"in[{lo},{hi}]?"
        if r: lo = mid + 1
        else: hi = mid
    return hi

def cell(arg):
    try:
        return cell0(arg)
    except Exception as e:
        return arg[0], arg[1], [(0, f"ERROR:{type(e).__name__}")], 0

def cell0(arg):
    a, b, kmax, wall, cad, maxsol = arg
    global CAD, MAXSOL; CAD = cad; MAXSOL = maxsol
    Rs = []; t0 = time.time(); res = []
    for k in range(1, kmax + 1):
        start = (Rs[-1] if Rs and isinstance(Rs[-1], int) else 1)
        R = rado(a, b, k, Rs, start, wall)
        Rs.append(R); res.append((k, R))
        if not isinstance(R, int): break
    return a, b, res, round(time.time() - t0)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--bmax", type=int, default=12); ap.add_argument("--kmax", type=int, default=3)
    ap.add_argument("--workers", type=int, default=11); ap.add_argument("--wall", type=int, default=600); ap.add_argument("--cadical", default="")
    ap.add_argument("--maxsol", type=int, default=3_000_000); A = ap.parse_args()
    cad = A.cadical
    if not cad:
        import shutil
        cad = os.path.join(tempfile.gettempdir(), "eq4_cadical"); shutil.copy(os.path.join(ROOT, "bin_linux", "cadical"), cad); os.chmod(cad, 0o755)
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["a"]), int(r["b"])))
    jobs = [(a, b, A.kmax, A.wall, cad, A.maxsol) for b in range(2, A.bmax + 1) for a in range(1, 2 * b + 2) if gcd(a, b) == 1 and (a, b) not in done]
    jobs.sort(key=lambda j: j[1])
    new = not os.path.exists(OUT); fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "k", "R", "cell_seconds"]); fh.flush()
    print(f"[{now()}] a(x-y)=b(z+w): {len(jobs)} cells (b <= {A.bmax}, a <= 2b+1), k <= {A.kmax}, {A.workers} workers, {A.wall}s per test", flush=True)
    t0 = time.time(); fin = 0; wt = sum(j[1] ** 4 for j in jobs); wd = 0
    with ProcessPoolExecutor(A.workers) as ex:
        futs = [ex.submit(cell, j) for j in jobs]
        try:
            for fu in as_completed(futs):
                a, b, res, sec = fu.result(); fin += 1; wd += b ** 4
                for k, R in res: w.writerow([now(), a, b, k, R, sec])
                fh.flush(); os.fsync(fh.fileno())
                el = time.time() - t0
                print(f"[{now()}] {fin}/{len(jobs)} (a,b)=({a},{b}): " + ", ".join(f"R{k}={R}" for k, R in res) + f" ({sec}s) | ETA about {el/max(wd,1)*(wt-wd)/60:.0f} min", flush=True)
        except KeyboardInterrupt:
            print("Ctrl+C: stopping (finished cells are saved)"); ex.shutdown(wait=False, cancel_futures=True); return
    print("done (results/eq4_rado.csv)")

if __name__ == "__main__":
    main()

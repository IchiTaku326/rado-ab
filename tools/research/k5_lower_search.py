# -*- coding: utf-8 -*-
r"""Lower bounds for k-colour Rado numbers of a(x-y)=bz by searching good colourings of [1,n] (2026-11-02 JST).
Started because 108 found that [1,243] HAS a good 5-colouring for 3(x-y)=z, so R5(3(x-y)=z) > 243 = 3^5 (the guess R_k = a^k fails).
For each n in the list: the formula of [1,n] (all solutions) is split into first-fit cubes of the first D numbers, solved in
parallel (MiniSat, --cube-wall seconds each); the FIRST satisfiable cube gives a colouring, which is CHECKED DIRECTLY against
all solutions and saved as results\c1_k5\cert_a{a}_b{b}_k{k}_n{n}.json -> R_k > n (a proof of the lower bound).
If no cube is satisfiable within the limits, the row says NOT_FOUND (this is NOT an upper bound) and the search stops.
Resumable: results\k5_lower.csv.  Progress with cubes done / ETA for the current n.
v2 (11-02 19:40): --struct 1 searches only colourings where the numbers with v_a(x)=1 have their own colour (seen in every
good 5-colouring so far); in the cloud this found [1,320] in 36 s (without it: no colouring of [1,260] in minutes).
Run: python tools\research\k5_lower_search.py --a 3 --b 1 --k 5 --workers 11 --depth 7 --cube-wall 60 260 280 300 330 360 400 450 500"""
import argparse, csv, json, os, sys, time, threading
import multiprocessing as mp
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9)); now = lambda: datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
OUT = os.path.join(ROOT, "results", "k5_lower.csv"); CERT = os.path.join(ROOT, "results", "c1_k5")
G = {}

def sols(a, b, n):
    out = []
    for z in range(a, n + 1, a):
        d = b * (z // a)
        for y in range(1, n - d + 1): out.append((y + d, y, z))
    return out

def va(x, a):
    j = 0
    while x % a == 0: x //= a; j += 1
    return j

def init(a, b, k, n, struct=0):
    v = lambda x, c: k * (x - 1) + c + 1
    cl = [[v(x, c) for c in range(k)] for x in range(1, n + 1)]
    if struct:      # 11-02 v2: search only colourings in which the numbers with v_a(x) = 1 have their own colour 0
        for x in range(1, n + 1):          # (seen in every good 5-colouring found so far; a search restriction, results are still checked)
            if va(x, a) == 1: cl.append([v(x, 0)])
            elif va(x, a) == 0: cl.append([-v(x, 0)])
    for x in range(1, n + 1):
        for c in range(k):
            for d in range(c + 1, k): cl.append([-v(x, c), -v(x, d)])
    for (x, y, z) in sols(a, b, n):
        T = sorted({x, y, z})
        for c in range(k): cl.append([-v(t, c) for t in T])
    G.update(a=a, b=b, k=k, n=n, cl=cl)

def solve(cube):
    from pysat.solvers import Solver
    k, n = G["k"], G["n"]; v = lambda x, c: k * (x - 1) + c + 1
    xs = G.get("cubexs") or list(range(1, n + 1))
    assum = [v(xs[i], int(c)) for i, c in enumerate(cube)]
    with Solver(name="minisat22", bootstrap_with=G["cl"]) as s:
        tm = threading.Timer(G["wall"], s.interrupt); tm.start()
        res = s.solve_limited(assumptions=assum, expect_interrupt=True); tm.cancel()
        if res:
            m = set(l for l in s.get_model() if l > 0)
            return cube, "SAT", [next(c for c in range(k) if v(x, c) in m) for x in range(1, n + 1)]
    return cube, ("TIMEOUT" if res is None else "UNSAT"), None

def worker_init(a, b, k, n, wall, struct=0, cubexs=None):
    init(a, b, k, n, struct); G["wall"] = wall; G["cubexs"] = cubexs

def firstfit(D, k):
    out = [""]
    for _ in range(D):
        out = [p + str(c) for p in out for c in range(min(k, (max(map(int, p)) + 2) if p else 1))]
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--a", type=int, default=3); ap.add_argument("--b", type=int, default=1)
    ap.add_argument("--k", type=int, default=5); ap.add_argument("--workers", type=int, default=11); ap.add_argument("--depth", type=int, default=7)
    ap.add_argument("--cube-wall", type=float, default=60); ap.add_argument("--struct", type=int, default=0)
    ap.add_argument("ns", type=int, nargs="+"); A = ap.parse_args()
    os.makedirs(CERT, exist_ok=True)
    done = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            if (int(r["a"]), int(r["b"]), int(r["k"])) == (A.a, A.b, A.k): done[int(r["n"])] = r["result"]
    new = not os.path.exists(OUT); fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "k", "n", "result", "cube", "seconds"]); fh.flush()
    for n in A.ns:
        if n in done:
            print(f"[{now()}] n={n}: already {done[n]}", flush=True)
            if done[n] != "SAT": break
            continue
        if A.struct:   # colour 0 is fixed (v_a = 1); cubes: first-fit with colours 1..k-1 on the first non-multiples of a
            cubes = ["".join(str(int(c) + 1) for c in p) for p in firstfit(A.depth, A.k - 1)]
        else:
            cubes = firstfit(A.depth, A.k)
        # v3 (11-02 18:35): cubes already finished for this n (UNSAT or time limit) are kept in a file and skipped after a restart
        prog = os.path.join(CERT, f"progress_a{A.a}_b{A.b}_k{A.k}_n{n}{'_s' if A.struct else ''}.txt")
        fin_c = set(open(prog).read().split()) if os.path.exists(prog) else set()
        if fin_c: print(f"[{now()}] n={n}: {len(fin_c)} cubes already finished earlier -> skipped", flush=True)
        total = len(cubes); cubes = [c for c in cubes if c not in fin_c]; pf = open(prog, "a")
        t0 = time.time(); found = None; cnt = 0
        print(f"[{now()}] R{A.k}({A.a}(x-y)={A.b}z): n={n}, {len(cubes)} cubes, {A.workers} workers, {A.cube_wall:.0f} s per cube", flush=True)
        xs = [x for x in range(1, n + 1) if x % A.a] if A.struct else None
        pool = mp.Pool(A.workers, initializer=worker_init, initargs=(A.a, A.b, A.k, n, A.cube_wall, A.struct, xs))
        try:
            last = 0
            for cube, st, col in pool.imap_unordered(solve, cubes):
                cnt += 1
                if st == "SAT": found = (cube, col); break
                pf.write(cube + "\n"); pf.flush()
                if time.time() - last > 60:
                    last = time.time(); el = time.time() - t0
                    print(f"[{now()}]   n={n}: {cnt + len(fin_c)}/{total} cubes without a colouring, {el/60:.0f} min, at most ~{el/cnt*(len(cubes)-cnt)/60:.0f} min more", flush=True)
        except KeyboardInterrupt:
            pool.terminate(); print("Ctrl+C: stopped (finished cubes of this n are kept; a restart continues with the rest)"); return
        pool.terminate(); pool.join(); pf.close()
        sec = round(time.time() - t0)
        if found:
            cube, col = found; C = {x: col[x - 1] for x in range(1, n + 1)}
            bad = [s for s in sols(A.a, A.b, n) if C[s[0]] == C[s[1]] == C[s[2]]]
            assert not bad, "colouring check failed"
            json.dump({"a": A.a, "b": A.b, "k": A.k, "n": n, "coloring": col, "cube": cube, "struct": A.struct, "checked": "all solutions"},
                      open(os.path.join(CERT, f"cert_a{A.a}_b{A.b}_k{A.k}_n{n}.json"), "w"))
            w.writerow([now(), A.a, A.b, A.k, n, "SAT", cube, sec]); fh.flush(); os.fsync(fh.fileno())
            print(f"[{now()}] n={n}: GOOD COLOURING FOUND and checked -> R{A.k}({A.a}(x-y)={A.b}z) > {n}  ({sec} s)", flush=True)
        else:
            w.writerow([now(), A.a, A.b, A.k, n, "NOT_FOUND", "", sec]); fh.flush(); os.fsync(fh.fileno())
            print(f"[{now()}] n={n}: no colouring found within the limits (NOT an upper bound) -> stop", flush=True); break
    print("done (results\\k5_lower.csv, results\\c1_k5\\)")

if __name__ == "__main__":
    mp.freeze_support(); main()

# -*- coding: utf-8 -*-
r"""VERSION 2 (elements ordered by degree = most constrained first; work queue, split cubes are solved at once).
Cube-and-conquer on the SMALL set S (k colours):  S = {a*m : m <= K} U {x = n (mod b)}  (see subset_k.py).
If every cube is UNSAT, S is not k-colourable, so [1,n] is not k-colourable.
Cubes = first-fit colour sequences of the first D elements of S (smallest first; colour names are fixed by first fit).
Each cube is solved by MiniSat with a wall limit (--cube-wall); a cube that times out is SPLIT (3 more elements coloured)
and its children are solved later.  A SAT cube = a colouring of S (S is colourable: no upper bound from S, stop that job).
11 processes; every finished cube is one row in results\subset_cubes.csv (flush+fsync) -> Ctrl+C is safe, restart continues.
Progress: open cubes / finished cubes / ETA (rough, from the rate of finished cubes).
Run: python tools\subset_cubes.py --workers 11 --depth 6 --cube-wall 600 4,5,4,741,141 5,3,2,399,103 4,6,5,1501,241"""
import csv, os, sys, threading, time
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "subset_cubes2.csv")
_CACHE = {}


def build(job):
    if job in _CACHE: return _CACHE[job]
    k, a, b, n, K = job.split(","); k, a, b, n = int(k), int(a), int(b), int(n); K = (n // a) if K == "all" else int(K)
    r = n % b
    S0 = [x for x in range(1, n + 1) if (x % a == 0 and x <= a * K) or x % b == r]
    inset = set(S0); trip = []; deg = {x: 0 for x in S0}
    q = 1
    while b * q <= n - 1 and a * q <= n:
        d, z = b * q, a * q
        if z in inset:
            for y in S0:
                if y + d > n: break
                if y + d in inset:
                    T = tuple(sorted({y, y + d, z})); trip.append(T)
                    for t in T: deg[t] += 1
        q += 1
    S = sorted(S0, key=lambda x: (-deg[x], x))          # most constrained first (lookahead-like order); first fit in this order
    idx = {x: i for i, x in enumerate(S)}; v = lambda x, c: k * idx[x] + c + 1
    cl = []
    for i, x in enumerate(S):
        cl.append([v(x, c) for c in range(min(k, i + 1))])
        for c in range(i + 1, k): cl.append([-v(x, c)])
    for T in trip:
        for c in range(k): cl.append([-v(t, c) for t in T])
    _CACHE[job] = (k, len(S), cl, v, S)
    return _CACHE[job]


def solve_cube(arg):
    job, cube, wall = arg
    from pysat.solvers import Solver
    k, ns, cl, v, S = build(job)
    assum = [v(S[i], int(c)) for i, c in enumerate(cube)]
    t0 = time.time()
    with Solver(name="minisat22", bootstrap_with=cl) as s:
        tm = threading.Timer(wall, s.interrupt); tm.start()
        res = s.solve_limited(assumptions=assum, expect_interrupt=True); tm.cancel()
    return job, cube, ("TIMEOUT" if res is None else ("SAT" if res else "UNSAT")), round(time.time() - t0, 1)


def firstfit(prefix, extra, k):
    out = [prefix]
    for _ in range(extra):
        nxt = []
        for p in out:
            m = max((int(c) for c in p), default=-1)
            for c in range(min(k, m + 2)): nxt.append(p + str(c))
        out = nxt
    return out


def main():
    args = sys.argv[1:]; W, D, cw = 11, 6, 600.0
    while args and args[0].startswith("--"):
        key, val = args[0], args[1]; args = args[2:]
        if key == "--workers": W = int(val)
        elif key == "--depth": D = int(val)
        elif key == "--cube-wall": cw = float(val)
    jobs = args
    st = {j: {} for j in jobs}            # job -> cube -> status (UNSAT/SAT/SPLIT)
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            if r["job"] in st: st[r["job"]][r["cube"]] = r["status"]
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "job", "cube", "status", "seconds"]); fh.flush()
    def row(job, cube, status, sec):
        w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), job, cube, status, sec]); fh.flush(); os.fsync(fh.fileno())
        st[job][cube] = status
    def open_cubes(job):
        k = int(job.split(",")[0]); out = []; stack = firstfit("0", D - 1, k)
        while stack:
            c = stack.pop()
            s_ = st[job].get(c)
            if s_ == "SPLIT": stack += firstfit(c, 3, k)
            elif s_ not in ("UNSAT", "SAT"): out.append(c)
        return out
    t0 = time.time(); nfin = 0
    Q = {j: [] for j in jobs}                    # one queue per job, taken in turn (round robin) so every job advances
    for j in jobs:
        if "SAT" in st[j].values(): print(f"{j}: already SAT -> skipped", flush=True); continue
        Q[j] = [(j, c, cw) for c in open_cubes(j)]
    print(f"[{datetime.now(JST):%H:%M:%S}] open cubes: " + ", ".join(f"{j}: {len(Q[j])}" for j in jobs), flush=True)
    pool = mp.Pool(W); pending = {}; dead = set(); turn = 0; last = 0.0
    fin = {j: 0 for j in jobs}; spl = {j: 0 for j in jobs}
    try:
        while any(Q[j] for j in jobs if j not in dead) or pending:
            live = [j for j in jobs if j not in dead and Q[j]]
            while live and len(pending) < W:
                j = live[turn % len(live)]; turn += 1
                item = Q[j].pop(0)
                pending[(item[0], item[1])] = (pool.apply_async(solve_cube, (item,)), time.time())
                live = [j for j in jobs if j not in dead and Q[j]]
            time.sleep(0.5)
            for key, (ar, ts) in list(pending.items()):
                if not ar.ready(): continue
                del pending[key]; job, cube, res, sec = ar.get(); nfin += 1; fin[job] += 1
                if res == "TIMEOUT":
                    row(job, cube, "SPLIT", sec); spl[job] += 1; k = int(job.split(",")[0])
                    Q[job] = [(job, c, cw) for c in firstfit(cube, 3, k)] + Q[job]
                else:
                    row(job, cube, res, sec)
                    if res == "SAT":
                        print(f"   {job}: cube {cube} SAT -> S is colourable, job stopped", flush=True); dead.add(job); Q[job] = []
                if job not in dead and not Q[job] and not any(p[0] == job for p in pending):
                    print(f"*** {job}: ALL cubes UNSAT -> S is not colourable -> [1,n] is not colourable", flush=True)
            if time.time() - last > 60:                # progress every minute
                last = time.time(); el = time.time() - t0
                parts = []
                for j in jobs:
                    if j in dead: parts.append(f"{j}: stopped (SAT)"); continue
                    op = len(Q[j]) + sum(1 for p in pending if p[0] == j)
                    eta = (el / fin[j] * op / 60) if fin[j] else float("nan")
                    parts.append(f"{j}: done {fin[j]} (split {spl[j]}), open {op}, ETA ~{eta:.0f} min if no more splits")
                old = max([time.time() - ts for (_, ts) in pending.values()] + [0])
                print(f"[{datetime.now(JST):%H:%M:%S}] elapsed {el/60:.0f} min | " + " | ".join(parts)
                      + f" | running {len(pending)} (oldest {old/60:.0f} min, limit {cw/60:.0f} min)", flush=True)
    except KeyboardInterrupt:
        print("Ctrl+C: stopped (finished cubes are saved)")
    finally:
        pool.terminate()
    print("done (results\\subset_cubes2.csv)")


if __name__ == "__main__":
    main()

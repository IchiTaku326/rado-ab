# -*- coding: utf-8 -*-
r"""5 colours, R5(3(x-y)=2z): the small set S (K = R4 = 103) at n = 399 turned out COLOURABLE (80).  Try to EXTEND that colouring
of S to a colouring of all of [1, 399]  ->  if it works, R5(3(x-y)=2z) >= 400 (a new lower bound; it was >= 399).
1) colour S again (the SAT cube 01223303 found by 80) and keep the colours of S;
2) 11 processes on the FULL CNF of [1, n] (5 colours), MiniSat:  worker 0 FORCES the colours of S (assumptions);
   workers 1..10 only PREFER them (phases) with different random preferences for the other numbers;
   plus a last check: S with K = all (every multiple of 3) at the same n.
A colouring found is checked against every solution of 3(x-y) = 2z and saved as results\c5_32\cert_n{n}.json.
Each worker stops after --wall seconds.  Results in results\c5_32\extend.csv (Ctrl+C is safe, nothing to resume).
Run: python tools\extend_s.py --n 399 --wall 7200"""
import csv, json, os, random, sys, threading, time
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
JST = timezone(timedelta(hours=9))
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "c5_32"); os.makedirs(D, exist_ok=True)
A, B, K = 3, 2, 5


def full_cnf(n):
    v = lambda x, c: (x - 1) * K + c + 1
    cl = [[v(x, c) for c in range(K)] for x in range(1, n + 1)]
    s = 1
    while B * s <= n - 1 and A * s <= n:
        d, z = B * s, A * s
        for y in range(1, n - d + 1):
            T = sorted({y, y + d, z})
            for c in range(K): cl.append([-v(t, c) for t in T])
        s += 1
    return cl, v


def check(n, col):
    s = 1; bad = 0
    while B * s <= n - 1 and A * s <= n:
        d, z = B * s, A * s
        for y in range(1, n - d + 1):
            if col[y] == col[y + d] == col[z]: bad += 1
        s += 1
    return bad


def s_colouring(n):
    import subset_cubes as sc
    from pysat.solvers import Solver
    k, ns, cl, v, S = sc.build(f"5,3,2,{n},103")
    cube = "01223303"
    with Solver(name="minisat22", bootstrap_with=cl) as s:
        if not s.solve(assumptions=[v(S[i], int(c)) for i, c in enumerate(cube)]): return None
        m = set(l for l in s.get_model() if l > 0)
    return {x: next(c for c in range(k) if v(x, c) in m) for x in S}


def work(args):
    wid, n, sc_col, wall = args
    from pysat.solvers import Solver
    cl, v = full_cnf(n); rnd = random.Random(wid)
    t0 = time.time()
    with Solver(name="minisat22", bootstrap_with=cl) as s:
        if wid == 0:
            assum = [v(x, c) for x, c in sc_col.items()]
        else:
            assum = []
            ph = []
            for x in range(1, n + 1):
                c0 = sc_col.get(x, rnd.randrange(K))
                ph += [v(x, c) if c == c0 else -v(x, c) for c in range(K)]
            s.set_phases(ph)
        tm = threading.Timer(wall, s.interrupt); tm.start()
        r = s.solve_limited(assumptions=assum, expect_interrupt=True); tm.cancel()
        col = None
        if r:
            m = set(l for l in s.get_model() if l > 0)
            col = [None] + [next(c for c in range(K) if v(x, c) in m) for x in range(1, n + 1)]
    return wid, ("TIMEOUT" if r is None else ("SAT" if r else "UNSAT")), round(time.time() - t0, 1), col


def main():
    args = sys.argv[1:]; n, wall = 399, 7200.0
    while args:
        if args[0] == "--n": n = int(args[1])
        elif args[0] == "--wall": wall = float(args[1])
        args = args[2:]
    out = os.path.join(D, "extend.csv"); new = not os.path.exists(out)
    fh = open(out, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "n", "worker", "mode", "result", "seconds"])
    sc_col = s_colouring(n)
    if sc_col is None: print("could not re-colour S (cube no longer SAT?)"); return
    print(f"[{datetime.now(JST):%H:%M:%S}] colouring of S ({len(sc_col)} numbers) found again; 11 workers on [1,{n}], wall {wall/60:.0f} min each", flush=True)
    t0 = time.time()
    with mp.Pool(11) as pool:
        for wid, res, sec, col in pool.imap_unordered(work, [(i, n, sc_col, wall) for i in range(11)]):
            mode = "forced S colours" if wid == 0 else "prefer S colours"
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), n, wid, mode, res, sec]); fh.flush(); os.fsync(fh.fileno())
            print(f"[{datetime.now(JST):%H:%M:%S}] worker {wid} ({mode}): {res} ({sec}s), elapsed {(time.time()-t0)/60:.0f} min (each stops at {wall/60:.0f} min)", flush=True)
            if res == "SAT":
                bad = check(n, col)
                cert = os.path.join(D, f"cert_n{n}.json")
                json.dump({"a": A, "b": B, "k": K, "n": n, "coloring": col[1:], "monochromatic": bad,
                           "jst_time": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")}, open(cert, "w"))
                print(f"*** [1,{n}] IS 5-colourable (check: {bad} monochromatic solutions) -> R5(3(x-y)=2z) >= {n + 1}.  saved {cert}", flush=True)
                if bad == 0: pool.terminate(); break
    print("done")


if __name__ == "__main__":
    main()

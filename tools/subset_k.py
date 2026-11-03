# -*- coding: utf-8 -*-
r"""k colours (k = 4, 5): is [1,n] not k-colourable already on a small set (like the 3-colour discovery)?
   S = {a*m : m <= K} U {x <= n : x = n (mod b)}      K = R_{k-1}(a,b) (the (k-1)-colour Rado number) or 'all' (= n/a)
   S not colourable  =>  [1,n] not colourable (sound).  Colour symmetry: the i-th element of S may only use colours 0..i (first fit).
Jobs: k,a,b,n,K  (K a number or all).  11 processes, MiniSat (pysat) with a wall-clock limit per job (interrupt -> TIMEOUT).
Results: results\subset_k.csv (one row per job; SAT/UNSAT rows are skipped on restart, TIMEOUT rows are retried only with
--retry).  Ctrl+C is safe.  Progress with a rough ETA.
Run: python tools\subset_k.py --wall 10800 --workers 11 4,5,4,741,141 ..."""
import csv, os, sys, threading, time
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "subset_k.csv")


def work(args):
    job, wall = args
    from pysat.solvers import Solver
    k, a, b, n, K = job.split(",")
    k, a, b, n = int(k), int(a), int(b), int(n); K = (n // a) if K == "all" else int(K)
    r = n % b
    S = [x for x in range(1, n + 1) if (x % a == 0 and x <= a * K) or x % b == r]
    idx = {x: i for i, x in enumerate(S)}; v = lambda x, c: k * idx[x] + c + 1
    t0 = time.time(); m = 0
    s = Solver(name="minisat22")
    for i, x in enumerate(S):
        s.add_clause([v(x, c) for c in range(min(k, i + 1))])          # first fit: element i uses colours 0..i
        for c in range(i + 1, k): s.add_clause([-v(x, c)])
    q = 1
    while b * q <= n - 1 and a * q <= n:
        d, z = b * q, a * q
        if z in idx:
            for y in S:
                if y + d > n: break
                if y + d in idx:
                    T = sorted({y, y + d, z})
                    for c in range(k): s.add_clause([-v(t, c) for t in T]); m += 1
        q += 1
    timer = threading.Timer(wall, s.interrupt); timer.start()
    res = s.solve_limited(expect_interrupt=True); timer.cancel(); s.delete()
    st = "TIMEOUT" if res is None else ("SAT" if res else "UNSAT")
    return job, len(S), m, st, round(time.time() - t0, 1)


def main():
    args = sys.argv[1:]; wall, W, retry = 10800.0, 11, False
    while args and args[0].startswith("--"):
        if args[0] == "--retry": retry = True; args = args[1:]; continue
        k, val = args[0], args[1]; args = args[2:]
        if k == "--wall": wall = float(val)
        elif k == "--workers": W = int(val)
    done = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done[r["job"]] = r["result"]
    jobs = [j for j in args if not (j in done and (done[j] in ("SAT", "UNSAT") or not retry))]
    print(f"{len(jobs)} jobs ({len(args) - len(jobs)} already done), {W} processes, wall {wall/3600:.1f} h per job", flush=True)
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "job", "subset_size", "clauses", "result", "seconds"]); fh.flush()
    t0 = time.time(); rounds = -(-len(jobs) // W) if jobs else 0
    with mp.Pool(W) as pool:
        for i, (job, size, m, st, sec) in enumerate(pool.imap_unordered(work, [(j, wall) for j in jobs]), 1):
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), job, size, m, st, sec]); fh.flush(); os.fsync(fh.fileno())
            el = time.time() - t0
            left = len(jobs) - i
            print(f"[{datetime.now(JST):%H:%M:%S}] {i}/{len(jobs)} {job}: S={size} numbers, {m} clauses -> {st} ({sec}s) | elapsed {el/60:.0f} min,"
                  f" at most about {(-(-left // W)) * wall / 3600:.1f} h more (every job stops at the wall limit)", flush=True)
    print("done (results\\subset_k.csv)")


if __name__ == "__main__":
    main()

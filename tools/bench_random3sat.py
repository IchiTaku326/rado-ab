# -*- coding: utf-8 -*-
r"""
Lv0 sanity pipeline: random k-SAT satisfiability-threshold scan.
Reproduces the known "phase transition" (random 3-SAT: ~4.267 clauses/variable
as n -> infinity, finite-size crossing at smaller n) with our own tooling.

Rules (see SPEC.md section 6):
  * resumable  : already-finished (n, alpha, trial) rows in the CSV are skipped
  * incremental: each result is appended + flushed to the CSV immediately
  * every row has a JST timestamp
  * deterministic: the instance for (n, alpha, trial) depends only on those
    numbers, so a resumed run produces exactly the same instances

Usage (PowerShell, from F:\sat_solver):
  ./5_run_threshold.bat
  python tools/bench_random3sat.py --n 100 --alpha-from 3.8 --alpha-to 4.8 --alpha-step 0.1 --trials 100 --workers 11
"""
import argparse, csv, os, random, sys, time
from datetime import datetime, timezone, timedelta
from multiprocessing import Pool

JST = timezone(timedelta(hours=9))
FIELDS = ["jst_time", "k", "n", "alpha", "trial", "m", "sat", "seconds", "solver"]


def gen_instance(k, n, m, seed):
    rng = random.Random(seed)
    cls = []
    for _ in range(m):
        vs = rng.sample(range(1, n + 1), k)
        cls.append([v if rng.random() < 0.5 else -v for v in vs])
    return cls


def solve_builtin(cls, n):
    """Tiny DPLL (unit propagation). Only a fallback for small n / testing."""
    sys.setrecursionlimit(10000)

    def dpll(clauses, assign):
        while True:
            unit = None
            new = []
            for c in clauses:
                if any(assign.get(abs(l)) == (l > 0) for l in c):
                    continue
                rest = [l for l in c if abs(l) not in assign]
                if not rest:
                    return False
                if len(rest) == 1 and unit is None:
                    unit = rest[0]
                new.append(rest)
            clauses = new
            if unit is None:
                break
            assign = dict(assign)
            assign[abs(unit)] = unit > 0
        if not clauses:
            return True
        v = abs(clauses[0][0])
        for val in (True, False):
            a = dict(assign)
            a[v] = val
            if dpll(clauses, a):
                return True
        return False

    return dpll([list(c) for c in cls], {})


def solve(cls, n, backend):
    if backend == "pysat":
        from pysat.solvers import Cadical153
        with Cadical153(bootstrap_with=cls) as s:
            return s.solve()
    return solve_builtin(cls, n)


def work(task):
    k, n, alpha, trial, backend = task
    m = int(round(alpha * n))
    seed = k * 1000003 + n * 10007 + int(round(alpha * 1000)) * 101 + trial * 7919
    cls = gen_instance(k, n, m, seed)
    t = time.time()
    sat = solve(cls, n, backend)
    return (k, n, alpha, trial, m, int(sat), round(time.time() - t, 4), backend)


def load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                done.add((int(r["k"]), int(r["n"]), round(float(r["alpha"]), 6), int(r["trial"])))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--alpha-from", type=float, default=3.8)
    ap.add_argument("--alpha-to", type=float, default=4.8)
    ap.add_argument("--alpha-step", type=float, default=0.1)
    ap.add_argument("--trials", type=int, default=100)
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--out", default=None)
    ap.add_argument("--backend", choices=["auto", "pysat", "builtin"], default="auto")
    a = ap.parse_args()

    backend = a.backend
    if backend == "auto":
        try:
            import pysat  # noqa
            backend = "pysat"
        except ImportError:
            backend = "builtin"
            print("[warn] python-sat not found -> slow built-in DPLL (small n only). Run ./1_setup_python.bat")
    out = a.out or os.path.join("results", f"threshold_k{a.k}_n{a.n}.csv")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    alphas = []
    x = a.alpha_from
    while x <= a.alpha_to + 1e-9:
        alphas.append(round(x, 6))
        x += a.alpha_step
    done = load_done(out)
    tasks = [(a.k, a.n, al, t, backend) for al in alphas for t in range(a.trials)
             if (a.k, a.n, al, t) not in done]
    print(f"[{datetime.now(JST):%Y-%m-%d %H:%M:%S} JST] total={len(alphas)*a.trials} done={len(done)} todo={len(tasks)} backend={backend} -> {out}")

    new_file = not os.path.exists(out)
    with open(out, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(FIELDS)
            f.flush()
        with Pool(a.workers) as pool:
            for i, (k, n, al, tr, m, sat, sec, be) in enumerate(pool.imap_unordered(work, tasks, chunksize=4), 1):
                w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), k, n, al, tr, m, sat, sec, be])
                f.flush()
                os.fsync(f.fileno())
                if i % 100 == 0:
                    print(f"  {i}/{len(tasks)}")

    # summary: P(SAT) per alpha
    stat = {}
    with open(out, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s = stat.setdefault(round(float(r["alpha"]), 6), [0, 0])
            s[0] += int(r["sat"]); s[1] += 1
    print(f"\n[{datetime.now(JST):%Y-%m-%d %H:%M:%S} JST] P(SAT) by alpha  (n={a.n}, k={a.k})")
    for al in sorted(stat):
        print(f"  alpha={al:5.2f}  P(SAT)={stat[al][0]/stat[al][1]:.3f}  ({stat[al][1]} trials)")


if __name__ == "__main__":
    main()

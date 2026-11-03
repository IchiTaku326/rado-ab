"""Benchmark solvers on the SAME random sample of cubes (decides which backend to use for the cube workers).
Run (PowerShell):  ./15_bench.bat      -> results\\bench_solvers\\bench.csv / bench.txt  (JST stamped)
Solvers: pysat Glucose4, MapleChrono, MapleCM, Minisat22, MergeSat3, (if present) + the cadical binary (one process per cube)."""
import argparse, csv, os, random, subprocess, sys, tempfile, time
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rado_c1 import build_cnf, write_dimacs
from cube_search import enum_cubes

JST = timezone(timedelta(hours=9))
def now(): return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

def run_pysat(name, cl, assums, budget):
    from pysat.solvers import Solver
    S = Solver(name=name, bootstrap_with=cl)
    t0 = time.time(); res = []
    for a in assums:
        t1 = time.time()
        S.conf_budget(budget)
        r = S.solve_limited(assumptions=a)
        res.append(("SAT" if r is True else "UNSAT" if r is False else "UNKNOWN", time.time() - t1))
    S.delete()
    return res

def run_cadical(binp, cl, nvars, assums, budget):
    res = []
    for a in assums:
        fd, tmp = tempfile.mkstemp(suffix=".cnf"); os.close(fd)
        t1 = time.time()
        write_dimacs(tmp, cl + [[x] for x in a], nvars)
        p = subprocess.run([binp, "-q", "-c", str(budget), tmp], capture_output=True, text=True)
        st = "SAT" if "s SATISFIABLE" in p.stdout else "UNSAT" if "s UNSATISFIABLE" in p.stdout else "UNKNOWN"
        res.append((st, time.time() - t1)); os.remove(tmp)
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, default=4); ap.add_argument("--b", type=int, default=3)
    ap.add_argument("--k", type=int, default=4); ap.add_argument("--n", type=int, default=384)
    ap.add_argument("--depth", type=int, default=10)
    ap.add_argument("--sample", type=int, default=60); ap.add_argument("--budget", type=int, default=20000)
    ap.add_argument("--cadical", default=""); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--solvers", default="glucose4,maplechrono,maplecm,minisat22,mergesat3")
    ap.add_argument("--out", default="results/bench_solvers")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cubes = enum_cubes(a.a, a.b, a.k, a.depth)
    random.seed(a.seed); idx = sorted(random.sample(range(len(cubes)), min(a.sample, len(cubes))))
    cl, nvars, v = build_cnf(a.a, a.b, a.k, a.n)
    assums = [[v(j + 1, c) for j, c in enumerate(cubes[i])] for i in idx]
    print(f"[{now()} JST] cell a{a.a} b{a.b} k{a.k} n{a.n}: {len(cubes)} cubes, sample {len(idx)}, budget {a.budget} conflicts", flush=True)
    rows = []
    for nm in [s for s in a.solvers.split(",") if s]:
        try:
            r = run_pysat(nm, cl, assums, a.budget)
        except Exception as e:
            print(f"  {nm}: not available ({repr(e)[:60]})", flush=True); continue
        rows.append((nm, r))
        print(f"  {nm}: " + summ(r), flush=True)
    if a.cadical:
        r = run_cadical(a.cadical, cl, nvars, assums, a.budget)
        rows.append(("cadical-binary", r)); print("  cadical-binary: " + summ(r), flush=True)
    with open(os.path.join(a.out, "bench.txt"), "a", encoding="utf-8") as f:
        f.write(f"[{now()} JST] a{a.a} b{a.b} k{a.k} n{a.n} sample {len(idx)} budget {a.budget}\n")
        for nm, r in rows: f.write(f"  {nm}: {summ(r)}\n")
    with open(os.path.join(a.out, "bench.csv"), "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for nm, r in rows:
            for i, (st, s) in zip(idx, r): w.writerow([now(), a.a, a.b, a.k, a.n, nm, i, st, round(s, 3)])

def summ(r):
    sol = sum(1 for st, _ in r if st != "UNKNOWN"); tot = sum(s for _, s in r)
    return f"solved {sol}/{len(r)} within budget, total {tot:.1f}s, mean {tot/len(r):.3f}s/cube"

if __name__ == "__main__":
    main()

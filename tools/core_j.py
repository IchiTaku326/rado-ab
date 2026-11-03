# -*- coding: utf-8 -*-
r"""Experiment for task 2 (2026-10-31): can the UPPER bound be proved for a whole family b = a + j (j fixed) by a
"symbolic SAT" proof as in Chang-De Loera-Wesley (arXiv:2210.03262, Lemma 4.5)?  That needs an unsatisfiable set of numbers
whose SIZE DOES NOT GROW with a and whose members are polynomials in a.  For large a, N(a, a+j) = M + a - j(j^2+j+1).
For each (j, a): S = {a*m : m <= b^2+b+1} U {x = N (mod b)} at n = N, one selector per number, MiniSat with assumptions ->
an unsatisfiable core (numbers needed), shrunk by re-solving on the core until it stops shrinking (not minimal).
Output: results\core_j.csv (one row per cell: sizes, core size split into types, seconds), results\core_j\j{j}_a{a}.json
(the core numbers).  11 processes (or --workers; each cell < 1 GB for b <= 50), resumable, ETA (weights b^4).
Run: python tools\core_j.py --workers 11 1:7-40 2:15-41 3:40-47"""
import csv, json, os, sys, time
from math import gcd
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
JST = timezone(timedelta(hours=9))
RES = os.path.join(HERE, "..", "results"); OUT = os.path.join(RES, "core_j.csv"); JD = os.path.join(RES, "core_j")
MINIMAL = os.environ.get("CORE_MIN") == "1"          # v2: deletion-based MINIMAL core (every number needed) -> core_j_min.csv
if MINIMAL: OUT = os.path.join(RES, "core_j_min.csv")


def cell(arg):
    j, a = arg; b = a + j
    from pysat.solvers import Solver
    from conj_jobs import N
    t0 = time.time()
    M = b * (b * b + b + a + 1); n = N(a, b); K = b * b + b + 1; r = n % b
    S = [x for x in range(1, n + 1) if (x % a == 0 and x <= a * K) or x % b == r]
    idx = {x: i for i, x in enumerate(S)}; ns = len(S)
    v = lambda x, c: 3 * idx[x] + c + 1; sel = lambda x: 3 * ns + idx[x] + 1
    s = Solver(name="minisat22"); m = 0
    for x in S: s.add_clause([v(x, 0), v(x, 1), v(x, 2), -sel(x)])
    s.add_clause([v(a, 0)])                                    # colour symmetry (a is in S): w.l.o.g. colour 0
    q = 1
    while b * q <= n - 1 and a * q <= n:
        d, z = b * q, a * q
        if z in idx:
            for y in S:
                if y + d > n: break
                if y + d in idx:
                    T = sorted({y, y + d, z})
                    for c in range(3): s.add_clause([-v(t, c) for t in T]); m += 1
        q += 1
    core = [sel(x) for x in S]; it = 0; sizes = []
    while True:
        it += 1
        if s.solve(assumptions=core):
            s.delete(); return dict(j=j, a=a, b=b, n=n, S=ns, clauses=m, result="SAT", core=None, sizes=sizes, sec=round(time.time() - t0, 1))
        c2 = sorted(set(s.get_core() or core)); sizes.append(len(c2))
        if len(c2) >= len(core) or it >= 8: core = c2; break
        core = c2
    if MINIMAL:                                                # drop numbers one by one; keep the solver's core after each UNSAT
        cur = set(core)
        for l in sorted(core, reverse=True):                   # large numbers first
            if l not in cur: continue
            test = [x for x in cur if x != l]
            if not s.solve(assumptions=test):
                cur = set(s.get_core() or test)
        core = sorted(cur); sizes.append(len(core))
    s.delete()
    inv = {sel(x): x for x in S}; X = sorted(inv[l] for l in core)
    return dict(j=j, a=a, b=b, n=n, S=ns, clauses=m, result="UNSAT", core=X, sizes=sizes, sec=round(time.time() - t0, 1))


def kinds(d):
    a, b, n = d["a"], d["b"], d["n"]; X = d["core"]; r = n % b
    chain = [x for x in X if x % b == r]; mult = [x for x in X if x % b != r]
    both = [x for x in chain if x % a == 0]
    return len(chain), len(mult), len(both)


def main():
    args = sys.argv[1:]; W = 11
    if args[:1] == ["--workers"]: W = int(args[1]); args = args[2:]
    jobs = []
    for t in args:
        j, rng = t.split(":"); lo, hi = map(int, rng.split("-")); j = int(j)
        jobs += [(j, a) for a in range(lo, hi + 1) if gcd(a, a + j) == 1]
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["j"]), int(r["a"])))
    jobs = [x for x in jobs if x not in done]
    jobs.sort(key=lambda x: x[0] + x[1])                       # small b first
    os.makedirs(JD, exist_ok=True)
    new = not os.path.exists(OUT); fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "j", "a", "b", "n", "S", "clauses", "result", "core", "core_chain", "core_mult", "core_chain_and_mult", "core_sizes", "seconds"]); fh.flush()
    print(f"{len(jobs)} cells ({len(done)} already done), {W} processes", flush=True)
    t0 = time.time(); wsum = sum((j + a) ** 4 for j, a in jobs); wdone = 0
    try:
        from grid_rado import free_mem_gb
    except Exception:
        free_mem_gb = lambda: None
    with mp.Pool(W) as pool:
        for i, d in enumerate(pool.imap_unordered(cell, jobs), 1):
            if d["core"] is not None:
                json.dump(d, open(os.path.join(JD, f"j{d['j']}_a{d['a']}" + ("_min" if MINIMAL else "") + ".json"), "w"))
                kc, km, kb = kinds(d)
            else:
                kc = km = kb = ""
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), d["j"], d["a"], d["b"], d["n"], d["S"], d["clauses"], d["result"],
                        len(d["core"]) if d["core"] else "", kc, km, kb, " ".join(map(str, d["sizes"])), d["sec"]]); fh.flush(); os.fsync(fh.fileno())
            wdone += (d["j"] + d["a"]) ** 4; el = time.time() - t0
            print(f"[{datetime.now(JST):%H:%M:%S}] {i}/{len(jobs)} j={d['j']} a={d['a']}: {d['result']} S={d['S']} core={len(d['core']) if d['core'] else '-'} "
                  f"(chain {kc}, multiples {km}) {d['sec']}s | elapsed {el/60:.0f} min, ETA about {el / max(wdone, 1) * (wsum - wdone) / 60:.0f} min", flush=True)
    print(f"done ({OUT})")


if __name__ == "__main__":
    mp.freeze_support(); main()

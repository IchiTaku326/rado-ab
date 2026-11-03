# -*- coding: utf-8 -*-
r"""
Rado numbers R_k(a(x-y)=bz) by SAT.  Building block of the C1 search (see c1_search.py).

Definition used (same as Chang-De Loera-Wesley, arXiv:2210.03262, as far as we could read it):
  R_k(E) = smallest n such that every k-coloring of {1..n} has a monochromatic positive solution
  (x, y, z in {1..n}, not necessarily distinct) of E.   Here E:  a*(x-y) = b*z.

Sub-commands
  gen     write a DIMACS CNF
  solve   solve one instance (one seed) and print ONE json line; saves a certificate if SAT
  rvalue  find R by increasing n (for reproducing known values; small cases only)

Backends: pysat (pip install python-sat; works on Windows), cadical / kissat (external binaries).
Diversification: --seed permutes variable names, clause order and literal order.
"""
import argparse, json, os, random, subprocess, sys, tempfile, time
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def now():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")


def solutions(a, b, n):
    sols = set()
    for x in range(2, n + 1):
        for y in range(1, x):
            t = a * (x - y)
            if t % b == 0:
                z = t // b
                if 1 <= z <= n:
                    sols.add(frozenset((x, y, z)))
    return sols



# ---- implied clauses (scaling lemma) ------------------------------------------------------------------------
# The equation is homogeneous: if chi is a valid colouring of [1,n], then i -> chi(d*i) is a valid colouring of
# [1, n//d].  So if n//d >= R_j (j colours need at most n//d numbers), the multiples of d use at least j+1 colours.
# These clauses are IMPLIED by the original CNF (and invariant under colour permutations, so they combine with the
# first-fit symmetry breaking).  They only help the solver.  R_j (j<k) is computed by SAT and cached.
import json as _json, itertools as _it, math as _math


def _rj_cache_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "rj_cache.json")


def rj_value(a, b, j, max_j=3):
    """R_j(a,b) for j colours (exact, by SAT; cached). None if j > max_j (too expensive -> clause skipped)."""
    if j > max_j:
        return None
    g = _math.gcd(a, b); da = b // g; za = a // g
    if j == 1:
        return min(max(da * s + 1, za * s) for s in range(1, 3 * max(da, za) + 3))
    path = _rj_cache_path(); key = f"{a},{b},{j}"
    try:
        cache = _json.load(open(path, encoding="utf-8"))
    except Exception:
        cache = {}
    if key in cache:
        return cache[key]
    lo = rj_value(a, b, j - 1, max_j)          # j-1 colours fail at this n, so R_j > R_{j-1}-1;  R_j >= R_{j-1}
    n = lo
    sat_n = None
    while solve_stream_pysat(a, b, j, n) == "SAT":
        sat_n = n; n = int(n * 1.5) + 1
    lo_sat = sat_n if sat_n is not None else lo - 1       # largest known SAT (R_j >= R_{j-1}, so lo-1 is SAT)
    hi_unsat = n
    while hi_unsat - lo_sat > 1:
        mid = (lo_sat + hi_unsat) // 2
        if solve_stream_pysat(a, b, j, mid) == "SAT": lo_sat = mid
        else: hi_unsat = mid
    cache[key] = hi_unsat
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        _json.dump(cache, f, indent=1)
    os.replace(tmp, path)
    return hi_unsat


def implied_clauses(a, b, k, n, v, max_j=3):
    """list of implied clauses (see above).  v(j,c) = variable of 'number j has colour c'."""
    R = {}
    for j in range(1, k):
        r = rj_value(a, b, j, max_j)
        if r is not None:
            R[j] = r
    out = []
    if not R:
        return out
    d = 1
    while n // d >= R[min(R)]:
        m = n // d
        jmax = max(j for j in R if m >= R[j])
        for C in _it.combinations(range(k), jmax):
            out.append([v(d * i, c) for i in range(1, m + 1) for c in range(k) if c not in C])
        d += 1
    return out



# ---- implied clauses, level 2: conditional forced equalities (proved by SAT for j colours, cached) --------------
# Fact (computed rigorously by SAT, see tools/forced.py): in EVERY valid j-colouring of [1, a^j - 1] the numbers with the same
# a-adic valuation level L may be forced to have one colour ("uniform"), and two levels may be forced to differ.
# Consequence for k > j colours on [1,n]: for d >= 1 with d*(a^j-1) <= n and every set C of j colours: IF every d*i (i<=a^j-1) has a
# colour in C, THEN d*[1,a^j-1] is a valid j-colouring, so the forced facts hold for d*x.   Clause = (some d*i has a colour outside C) OR fact.
def _val(a, x):
    e = 0
    while x % a == 0:
        x //= a; e += 1
    return e


def _forced_cache_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "forced_cache.json")


def forced_info(a, b, j):
    """-> {'uniform': [levels], 'diff': [[l1,l2],...]} for valid j-colourings of [1,a^j-1]; None if no colouring / too big."""
    key = f"{a},{b},{j}"; path = _forced_cache_path()
    try:
        cache = _json.load(open(path, encoding="utf-8"))
    except Exception:
        cache = {}
    if key in cache:
        return cache[key]
    from pysat.solvers import Glucose4
    n = a ** j - 1
    cl, nv, v = build_cnf(a, b, j, n, symbreak=False)
    S = Glucose4(bootstrap_with=cl)
    try:
        if not S.solve():
            cache[key] = None
        else:
            levels = {}
            for x in range(1, n + 1):
                levels.setdefault(_val(a, x), []).append(x)
            def can_differ(x, y):
                return any(S.solve(assumptions=[v(x, c), v(y, c2)]) for c in range(j) for c2 in range(j) if c != c2)
            uniform = [L for L in sorted(levels) if not any(can_differ(levels[L][0], x) for x in levels[L][1:])]
            diff = [[L1, L2] for L1 in sorted(levels) for L2 in sorted(levels) if L1 < L2 and
                    not any(S.solve(assumptions=[v(levels[L1][0], c), v(levels[L2][0], c)]) for c in range(j))]
            cache[key] = {"uniform": uniform, "diff": diff}
    finally:
        S.delete()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        _json.dump(cache, f, indent=1)
    os.replace(tmp, path)
    return cache[key]


def implied_clauses2(a, b, k, n, v, js=(2, 3)):
    out = []
    for j in js:
        if j >= k or a ** j - 1 < 1:
            continue
        info = forced_info(a, b, j)
        if not info or (not info["uniform"] and not info["diff"]):
            continue
        m0 = a ** j - 1
        levels = {}
        for x in range(1, m0 + 1):
            levels.setdefault(_val(a, x), []).append(x)
        for d in range(1, n // m0 + 1):
            for C in _it.combinations(range(k), j):
                cond = [v(d * i, c) for i in range(1, m0 + 1) for c in range(k) if c not in C]
                for L in info["uniform"]:
                    rep = levels[L][0]
                    for x in levels[L][1:]:
                        for c in C:
                            out.append(cond + [-v(d * x, c), v(d * rep, c)])
                for L1, L2 in info["diff"]:
                    r1, r2 = levels[L1][0], levels[L2][0]
                    for c in C:
                        out.append(cond + [-v(d * r1, c), -v(d * r2, c)])
    return out


def build_cnf(a, b, k, n, symbreak=True, implied=False):
    def v(j, c):
        return (j - 1) * k + c + 1
    base = n * k

    def u(j, c):  # "color c is used somewhere in 1..j", c in 0..k-2
        return base + (j - 1) * (k - 1) + c + 1
    cl = []
    for j in range(1, n + 1):
        cl.append([v(j, c) for c in range(k)])
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                cl.append([-v(j, c1), -v(j, c2)])
    for S in solutions(a, b, n):
        for c in range(k):
            cl.append([-v(j, c) for j in sorted(S)])
    nvars = base
    if symbreak and k > 1:
        nvars = base + n * (k - 1)
        for j in range(1, n + 1):
            for c in range(k - 1):
                cl.append([-v(j, c), u(j, c)])
                if j > 1:
                    cl.append([-u(j - 1, c), u(j, c)])
                    cl.append([-u(j, c), u(j - 1, c), v(j, c)])
                else:
                    cl.append([-u(j, c), v(j, c)])
            for c in range(1, k):
                if j == 1:
                    cl.append([-v(1, c)])
                else:
                    cl.append([-v(j, c), u(j - 1, c - 1)])
    if implied:
        cl.extend(implied_clauses(a, b, k, n, v))
        if int(implied) >= 2:
            cl.extend(implied_clauses2(a, b, k, n, v))
    return cl, nvars, v


def iter_cnf(a, b, k, n, symbreak=True, implied=False):
    """STREAMING version of build_cnf for big n: yields the same clauses (up to repeated identical clauses and order)
    without holding the set of solution sets or the clause list in memory, and enumerates the solutions directly
    (x-y = (b/g)*s, z = (a/g)*s) instead of looping over all pairs x>y.  Returns nothing; use nvars_of(n, k, symbreak)."""
    import math
    g = math.gcd(a, b); da = b // g; za = a // g
    def v(j, c):
        return (j - 1) * k + c + 1
    base = n * k
    def u(j, c):
        return base + (j - 1) * (k - 1) + c + 1
    for j in range(1, n + 1):
        yield [v(j, c) for c in range(k)]
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                yield [-v(j, c1), -v(j, c2)]
    s = 1
    while da * s <= n - 1 and za * s <= n:
        d = da * s; z = za * s
        for y in range(1, n - d + 1):
            S = sorted({y + d, y, z})
            for c in range(k):
                yield [-v(j, c) for j in S]
        s += 1
    if symbreak and k > 1:
        for j in range(1, n + 1):
            for c in range(k - 1):
                yield [-v(j, c), u(j, c)]
                if j > 1:
                    yield [-u(j - 1, c), u(j, c)]
                    yield [-u(j, c), u(j - 1, c), v(j, c)]
                else:
                    yield [-u(j, c), v(j, c)]
            for c in range(1, k):
                if j == 1:
                    yield [-v(1, c)]
                else:
                    yield [-v(j, c), u(j - 1, c - 1)]
    if implied:
        for cl_ in implied_clauses(a, b, k, n, v):
            yield cl_
        if int(implied) >= 2:
            for cl_ in implied_clauses2(a, b, k, n, v):
                yield cl_


def nvars_of(n, k, symbreak=True):
    return n * k + (n * (k - 1) if symbreak and k > 1 else 0)


def solve_stream_pysat(a, b, k, n, implied=False, solver="cadical153"):
    """-> 'SAT' / 'UNSAT' with a low memory footprint (clauses go straight into the solver).
    solver: any pysat name.  2026-10-28: minisat22 was ~20x faster and used ~1/3 of the memory of CaDiCaL on 3-colour
    instances (VM test: (19,29) n=25896/25897 in 9 s / 1.6 GB; CaDiCaL on the PC 200-240 s)."""
    from pysat.solvers import Solver
    s = Solver(name=solver)
    try:
        for c in iter_cnf(a, b, k, n, implied=implied):
            s.add_clause(c)
        return "SAT" if s.solve() else "UNSAT"
    finally:
        s.delete()


def permute(cl, nvars, seed):
    if seed == 0:
        return cl, list(range(nvars + 1))
    rng = random.Random(seed)
    p = list(range(1, nvars + 1))
    rng.shuffle(p)
    mp = [0] + p                      # old var -> new var
    out = [[(mp[abs(l)] if l > 0 else -mp[abs(l)]) for l in c] for c in cl]
    for c in out:
        rng.shuffle(c)
    rng.shuffle(out)
    return out, mp


def write_dimacs(path, cl, nvars):
    with open(path, "w") as f:
        f.write(f"p cnf {nvars} {len(cl)}\n")
        for c in cl:
            f.write(" ".join(map(str, c)) + " 0\n")


def run_backend(cl, nvars, backend, binpath, timeout, proof=None):
    """returns (status, model_dict or None).  status in SAT / UNSAT / TIMEOUT / ERROR"""
    if backend == "pysat":
        from pysat.solvers import Cadical153
        with Cadical153(bootstrap_with=cl) as s:
            if s.solve():
                m = s.get_model()
                return "SAT", {abs(l): (l > 0) for l in m}
            return "UNSAT", None
    fd, path = tempfile.mkstemp(suffix=".cnf")
    os.close(fd)
    try:
        write_dimacs(path, cl, nvars)
        cmd = [binpath, "-q"] if backend == "kissat" else [binpath, "-q"]
        cmd.append(path)
        if proof:
            cmd.append(proof)
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "TIMEOUT", None
        model = {}
        status = None
        for line in p.stdout.splitlines():
            if line.startswith("s SATISFIABLE"):
                status = "SAT"
            elif line.startswith("s UNSATISFIABLE"):
                status = "UNSAT"
            elif line.startswith("v "):
                for tok in line[2:].split():
                    t = int(tok)
                    if t != 0:
                        model[abs(t)] = t > 0
        if status is None:
            return "ERROR", None
        return status, (model if status == "SAT" else None)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def solve_instance(a, b, k, n, seed, backend, binpath, timeout, outdir, proof=None):
    t0 = time.time()
    cl, nvars, v = build_cnf(a, b, k, n)
    pcl, mp = permute(cl, nvars, seed)
    status, model = run_backend(pcl, nvars, backend, binpath, timeout, proof)
    res = {"jst_time": now(), "a": a, "b": b, "k": k, "n": n, "seed": seed, "backend": backend,
           "status": status, "seconds": round(time.time() - t0, 2), "cert": ""}
    if status == "SAT":
        col = []
        for j in range(1, n + 1):
            cs = [c for c in range(k) if model.get(mp[v(j, c)], False)]
            if len(cs) != 1:
                res["status"] = "ERROR"; res["note"] = "bad model"
                return res
            col.append(cs[0])
        os.makedirs(outdir, exist_ok=True)
        cert = os.path.join(outdir, f"cert_a{a}_b{b}_k{k}_n{n}_seed{seed}.json")
        tmp = cert + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"a": a, "b": b, "k": k, "n": n, "seed": seed, "backend": backend,
                       "jst_time": res["jst_time"], "coloring": col}, f)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, cert)
        # independent verification (separate file, separate code path)
        here = os.path.dirname(os.path.abspath(__file__))
        vp = subprocess.run([sys.executable, os.path.join(here, "rado_verify.py"), cert],
                            capture_output=True, text=True)
        if vp.returncode != 0:
            res["status"] = "ERROR"; res["note"] = "verification failed: " + vp.stdout.strip()
        else:
            res["cert"] = cert
    return res


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gen", "solve", "rvalue"):
        p = sub.add_parser(name)
        p.add_argument("--a", type=int, required=True)
        p.add_argument("--b", type=int, required=True)
        p.add_argument("--k", type=int, required=True)
        if name != "rvalue":
            p.add_argument("--n", type=int, required=True)
        if name == "rvalue":
            p.add_argument("--start", type=int, default=2)
            p.add_argument("--max-n", type=int, default=2000)
        if name == "gen":
            p.add_argument("--out", required=True)
        else:
            p.add_argument("--seed", type=int, default=0)
            p.add_argument("--backend", choices=["pysat", "cadical", "kissat"], default="pysat")
            p.add_argument("--bin", default="cadical")
            p.add_argument("--timeout", type=float, default=None)
            p.add_argument("--outdir", default=os.path.join("results", "c1"))
            p.add_argument("--proof", default=None, help="DRAT proof path (cadical/kissat binaries only)")
    a = ap.parse_args()
    if a.cmd == "gen":
        cl, nv, _ = build_cnf(a.a, a.b, a.k, a.n)
        write_dimacs(a.out, cl, nv)
        print(f"wrote {a.out}: vars={nv} clauses={len(cl)}")
    elif a.cmd == "solve":
        r = solve_instance(a.a, a.b, a.k, a.n, a.seed, a.backend, a.bin, a.timeout, a.outdir, a.proof)
        print(json.dumps(r))
    else:
        n = a.start
        while n <= a.max_n:
            r = solve_instance(a.a, a.b, a.k, n, 0, a.backend, a.bin, a.timeout, a.outdir)
            print(f"[{r['jst_time']} JST] n={n} {r['status']} ({r['seconds']}s)", flush=True)
            if r["status"] == "UNSAT":
                print(f"R_{a.k}({a.a}(x-y)={a.b}z) = {n}")
                return
            if r["status"] != "SAT":
                print("stopped:", r); return
            n += 1
        print("max-n reached")


if __name__ == "__main__":
    main()


# ---- LAZY (counterexample-guided) solving, 2026-10-28: memory ~ the clauses that are really needed -------------------------
# The full CNF for 3 colours at n~45000 has ~90 million clauses (~8-10 GB in CaDiCaL).  Here the solver starts with the
# colour/symmetry clauses and a sample of the solution clauses; after each SAT answer the colouring is checked against
# ALL solutions and only the violated ones are added (incrementally: learned clauses are kept).  Correct by construction:
# UNSAT on a subset of the clauses => UNSAT on all; SAT with no violated solution => a valid colouring.
def solve_lazy_pysat(a, b, k, n, sample=0.02, max_add=200000, seed=1, log=None, solver="cadical153"):
    """-> ('SAT'|'UNSAT', info dict).  Needs pysat; uses numpy for the check if available."""
    import math, random as _r
    from pysat.solvers import Solver as _PS
    try:
        import numpy as np
    except Exception:
        np = None
    g = math.gcd(a, b); da = b // g; za = a // g
    def v(j, c):
        return (j - 1) * k + c + 1
    S = _PS(name=solver)
    rng = _r.Random(seed)
    added = 0
    try:
        # colour + symmetry clauses (the same as in iter_cnf, without the solution clauses)
        base = n * k
        def u(j, c):
            return base + (j - 1) * (k - 1) + c + 1
        for j in range(1, n + 1):
            S.add_clause([v(j, c) for c in range(k)])
            for c1 in range(k):
                for c2 in range(c1 + 1, k):
                    S.add_clause([-v(j, c1), -v(j, c2)])
        if k > 1:
            for j in range(1, n + 1):
                for c in range(k - 1):
                    S.add_clause([-v(j, c), u(j, c)])
                    if j > 1:
                        S.add_clause([-u(j - 1, c), u(j, c)]); S.add_clause([-u(j, c), u(j - 1, c), v(j, c)])
                    else:
                        S.add_clause([-u(j, c), v(j, c)])
                for c in range(1, k):
                    S.add_clause([-v(1, c)] if j == 1 else [-v(j, c), u(j - 1, c - 1)])
        svals = []
        s = 1
        while da * s <= n - 1 and za * s <= n:
            svals.append(s); s += 1
        # initial sample of solution clauses (all colours)
        for s in svals:
            d = da * s; z = za * s; m = n - d
            cnt = int(sample * m)
            for y in (rng.sample(range(1, m + 1), cnt) if cnt < m else range(1, m + 1)):
                S2 = sorted({y + d, y, z})
                for c in range(k):
                    S.add_clause([-v(j, c) for j in S2]); added += 1
        rounds = 0
        while True:
            rounds += 1
            if not S.solve():
                return "UNSAT", {"rounds": rounds, "added": added}
            model = S.get_model()
            col = [0] * (n + 1)
            pos = set(l for l in model[: n * k] if l > 0)
            for j in range(1, n + 1):
                for c in range(k):
                    if v(j, c) in pos:
                        col[j] = c; break
            viol = []
            if np is not None:
                C = np.array(col, dtype=np.int8)
                for s in svals:
                    d = da * s; z = za * s
                    ys = np.nonzero((C[1:n - d + 1] == C[1 + d:n + 1]) & (C[1:n - d + 1] == C[z]))[0] + 1
                    for y in ys.tolist():
                        viol.append((s, y, int(C[z])))
            else:
                for s in svals:
                    d = da * s; z = za * s; cz = col[z]
                    for y in range(1, n - d + 1):
                        if col[y] == cz and col[y + d] == cz:
                            viol.append((s, y, cz))
            if not viol:
                return "SAT", {"rounds": rounds, "added": added, "colouring": col[1:]}
            rng.shuffle(viol)
            for s, y, c in viol[:max_add]:
                d = da * s; z = za * s
                S.add_clause([-v(j, c) for j in sorted({y + d, y, z})]); added += 1
            if log:
                log(f"round {rounds}: {len(viol)} violated, added {min(len(viol), max_add)}, total {added}")
    finally:
        S.delete()

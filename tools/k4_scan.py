# -*- coding: utf-8 -*-
r"""4-colour values for a < b (open problem 3: there was only (2,3) = 226).  Upper bound by the SMALL set S
(K = R3(a,b), as for 741 / 1501), scanning n upward from R3+1:
   [1,n] colourable  =>  S(n) colourable,  so  S(n) UNSAT  =>  R4 <= n   (rigorous; S is NOT monotone in n -> no binary search).
Each S(n) gets one quick MiniSat run (--wall, with symmetry + implied clauses, the same CNF as subset_cubes.py).
A cell's scan stops when, after the first n whose S is not quickly SAT (the FRONTIER F), --run more n in a row were not
quickly SAT either (or n reaches 4*b*R3).  F with UNSAT  -> upper bound U = F.  F with TIMEOUT -> decided by subset_cubes.py
(85_k4_ab.ps1 does that; this tool reads subset_cubes.csv: a SAT cube = S colourable, a complete UNSAT tree = UNSAT).
Cells: k,a,b,K   e.g.  4,3,4,109 4,4,5,180 4,2,5,181 4,3,5,186
Output: results\k4_scan.csv (one row per n, flush+fsync, restart continues), results\k4_frontier.txt (job status per cell).
v2 (2026-10-31 11:40): (1) watchdog: a MiniSat run that ignores its interrupt (4 runs hung for 2.5 h on 10-31) is recorded as
TIMEOUT after wall+60 s and the pool is restarted.  (2) a 4-colouring of [1,L] found by c1_search (results\c1_k4ab) makes
S(n) SAT for every n <= L (rigorous: [1,n] colourable => S(n) colourable), so those n need no S solve; c1 UNSAT at L+1 settles
R4 = L+1.  (3) a cell also stops after --tmax non-SAT n past the frontier.  Writes results\k4_todo.txt (first --ncubes TIMEOUT
jobs per cell above L, for subset_cubes) and results\k4_c1.txt (a b base maxn for c1_search).
Run: python tools\k4_scan.py --wall 120 --run 12 --tmax 6 --depth 7 4,3,4,109 ..."""
import csv, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
JST = timezone(timedelta(hours=9))
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
OUT = os.path.join(RES, "k4_scan.csv"); FRONT = os.path.join(RES, "k4_frontier.txt")
CUBES = os.path.join(RES, "subset_cubes.csv")
TODO = os.path.join(RES, "k4_todo.txt"); C1F = os.path.join(RES, "k4_c1.txt"); C1D = os.path.join(RES, "c1_k4ab")


def c1_info(k, a, b):
    """(largest n with a recorded 4-colouring of [1,n], smallest n recorded UNSAT) from c1_search"""
    f = os.path.join(C1D, f"c1_a{a}_b{b}_k{k}.csv"); L = U = None
    if os.path.exists(f):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            try: n = int(r["n"])
            except Exception: continue
            if r["status"] == "SAT": L = n if L is None else max(L, n)
            if r["status"] == "UNSAT": U = n if U is None else min(U, n)
    return L, U


def quick(arg):
    job, wall = arg
    from subset_cubes import solve_cube
    j, c, res, sec = solve_cube((job, "0", wall, 0.0, "mini"))
    return job, res, sec


def cubes_status(job, D):
    """SAT / UNSAT_CUBES / None from subset_cubes.csv (same tree as subset_cubes.py with --depth D)"""
    if not os.path.exists(CUBES): return None
    from subset_cubes import firstfit
    st = {}
    for r in csv.DictReader(open(CUBES, encoding="utf-8")):
        if r["job"] == job: st[r["cube"]] = r["status"]
    if not st: return None
    if "SAT" in st.values(): return "SAT"
    k = int(job.split(",")[0]); stack = firstfit("0", D - 1, k)
    while stack:
        c = stack.pop(); s_ = st.get(c)
        if s_ == "SPLIT": stack += firstfit(c, 3, k)
        elif s_ != "UNSAT": return None
    return "UNSAT_CUBES"


def main():
    args = sys.argv[1:]; W, wall, RUN, D, TMAX, NC = 11, 120.0, 12, 7, 6, 3
    while args and args[0].startswith("--"):
        key, val = args[0], args[1]; args = args[2:]
        if key == "--workers": W = int(val)
        elif key == "--wall": wall = float(val)
        elif key == "--run": RUN = int(val)
        elif key == "--depth": D = int(val)
        elif key == "--tmax": TMAX = int(val)
        elif key == "--ncubes": NC = int(val)
    cells = [tuple(int(t) for t in c.split(",")) for c in args]           # (k, a, b, K)
    res = {c: {} for c in cells}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            c = (int(r["k"]), int(r["a"]), int(r["b"]), int(r["K"]))
            if c in res: res[c][int(r["n"])] = r["result"]
    for c in cells:                                                          # results of subset_cubes override TIMEOUT
        k, a, b, K = c
        for n, s_ in list(res[c].items()):
            if s_ == "TIMEOUT":
                cs = cubes_status(f"{k},{a},{b},{n},{K}", D)
                if cs: res[c][n] = cs
    C1 = {}
    for c in cells:                                                          # c1 colourings: S(n) SAT for n <= L
        L, U1 = c1_info(c[0], c[1], c[2]); C1[c] = (L, U1)
        if L:
            for n in range(c[3] + 1, L + 1): res[c][n] = "SAT"
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "k", "a", "b", "n", "K", "result", "seconds"]); fh.flush()

    def state(c):
        """('done', F, status) or ('more', next_n)"""
        k, a, b, K = c; n = K + 1; F = None; run = 0; nt = 0; hi = 4 * b * K
        L, U1 = C1[c]
        if L is not None and U1 == L + 1: return ("done", U1, "UNSAT_C1")
        while n in res[c]:
            s_ = res[c][n]
            if F is None and s_ != "SAT":
                F = n
                if s_ in ("UNSAT", "UNSAT_CUBES"): return ("done", F, s_)
            if F is not None:
                run = run + 1 if s_ != "SAT" else 0; nt += s_ != "SAT"
                if s_ in ("UNSAT", "UNSAT_CUBES"): return ("done", F, res[c][F])
            if F is not None and (run >= RUN + 1 or nt >= TMAX): return ("done", F, res[c][F])
            n += 1
            if U1 is not None and n >= U1: return ("done", F or U1, res[c][F] if F else "UNSAT_C1")
        if n > hi: return ("done", F, res[c][F] if F else "NONE")
        return ("more", n)

    pool = mp.Pool(W); pending = {}; t0 = time.time(); last = 0.0; nd = 0
    try:
        while True:
            act = [c for c in cells if state(c)[0] == "more"]
            if not act and not pending: break
            # fill: next n per active cell (round robin), at most W in flight, never more than 2*W ahead per cell
            added = True                                                     # round robin over the cells; skip n that are known
            while added and len(pending) < W:                                # or running (v3: v2 stopped at the first known n,
                added = False                                                # so only 4 solves ran -> CPU almost idle)
                for c in act:
                    if len(pending) >= W: break
                    nxt = state(c)[1]; k, a, b, K = c
                    n = nxt
                    while (n in res[c] or (c, n) in pending) and n <= nxt + 3 * W: n += 1
                    if n > nxt + 3 * W or n > 4 * b * K: continue
                    pending[(c, n)] = (pool.apply_async(quick, ((f"{k},{a},{b},{n},{K}", wall),)), time.time()); added = True
            time.sleep(0.2)
            hung = [key for key, (ar, ts) in pending.items() if not ar.ready() and time.time() - ts > wall + 60]
            if hung:                                                         # watchdog: kill the pool, record TIMEOUT, resubmit the rest
                pool.terminate(); pool = mp.Pool(W)
                for key in hung:
                    c, n = key; res[c][n] = "TIMEOUT"; del pending[key]; nd += 1
                    w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), *c[:3], n, c[3], "TIMEOUT", round(wall, 1)]); fh.flush(); os.fsync(fh.fileno())
                    print(f"   {c[0]},{c[1]},{c[2]},{n},{c[3]}: no answer after {wall + 60:.0f}s -> TIMEOUT (watchdog, pool restarted)", flush=True)
                for key in list(pending):
                    c, n = key; k, a, b, K = c
                    pending[key] = (pool.apply_async(quick, ((f"{k},{a},{b},{n},{K}", wall),)), time.time())
            for key, (ar, ts) in list(pending.items()):
                if not ar.ready(): continue
                del pending[key]; c, n = key; job, r_, sec = ar.get(); nd += 1
                res[c][n] = r_
                w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), *c[:3], n, c[3], r_, sec]); fh.flush(); os.fsync(fh.fileno())
                if r_ != "SAT": print(f"   {job}: {r_} ({sec}s)", flush=True)
            if time.time() - last > 60:
                last = time.time(); el = time.time() - t0; parts = []
                for c in cells:
                    st = state(c); kn = sorted(res[c])
                    parts.append(f"({c[1]},{c[2]}) " + (f"done F={st[1]} {st[2]}" if st[0] == "done" else f"at n={st[1]}"))
                print(f"[{datetime.now(JST):%H:%M:%S}] elapsed {el/60:.0f} min, {nd} solves | " + " | ".join(parts)
                      + " | ETA: unknown until the frontier is reached (each solve <= " + f"{wall:.0f}s)", flush=True)
    except KeyboardInterrupt:
        print("interrupted: rows already written are kept; run again to continue"); pool.terminate(); sys.exit(1)
    pool.terminate()
    with open(FRONT, "w", encoding="utf-8") as f, open(TODO, "w", encoding="utf-8") as g, open(C1F, "w", encoding="utf-8") as h:
        for c in cells:
            st = state(c); k, a, b, K = c; L, U1 = C1[c]
            f.write(f"{k},{a},{b},{st[1]},{K} {st[2]}\n")
            print(f"FRONTIER ({a},{b}) k={k}: n={st[1]} {st[2]}  (S at every n from {K+1} to {st[1]-1} is colourable"
                  + (f"; [1,{L}] has a {k}-colouring" if L else "") + ")", flush=True)
            if st[2] in ("UNSAT", "UNSAT_CUBES", "UNSAT_C1"): continue
            tos = [n for n in sorted(res[c]) if res[c][n] == "TIMEOUT" and (L is None or n > L)][:NC]
            for n in tos: g.write(f"{k},{a},{b},{n},{K}\n")
            uns = [n for n, s_ in res[c].items() if s_.startswith("UNSAT")] + ([U1] if U1 else [])
            top = min(uns + [max(res[c]) + 1]) - 1
            base = (L + 1) if L else max(K + 1, (st[1] or K + 2) - 1)
            h.write(f"{a} {b} {base} {top}\n")


if __name__ == "__main__":
    mp.freeze_support(); main()

# -*- coding: utf-8 -*-
r"""(--cadical-wall T: a cube that MiniSat cannot solve within --cube-wall is tried by CaDiCaL (killable subprocess, T seconds) before it is split.
work queue since 2026-10-30 12:30: a timed-out cube is split at once, jobs in turn, progress every minute)
Cube-and-conquer on the SMALL set S (k colours):  S = {a*m : m <= K} U {x = n (mod b)}  (see subset_k.py).
If every cube is UNSAT, S is not k-colourable, so [1,n] is not k-colourable.
Cubes = first-fit colour sequences of the first D elements of S (smallest first; colour names are fixed by first fit).
Each cube is solved by MiniSat with a wall limit (--cube-wall); a cube that times out is SPLIT (3 more elements coloured)
and its children are solved later.  A SAT cube = a colouring of S (S is colourable: no upper bound from S, stop that job).
11 processes; every finished cube is one row in results\subset_cubes.csv (flush+fsync) -> Ctrl+C is safe, restart continues.
Progress: open cubes / finished cubes / ETA (rough, from the rate of finished cubes).
Run: python tools\subset_cubes.py --workers 11 --depth 6 --cube-wall 600 4,5,4,741,141 5,3,2,399,103 4,6,5,1501,241"""
import csv, os, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "subset_cubes.csv")
if os.environ.get("SUBSET_CUBES_OUT"): OUT = os.environ["SUBSET_CUBES_OUT"]      # for tests
_CACHE = {}
# j-colour Rado numbers R_j(a,b) for j = 1, 2, ... (R1 = max(a, b+1); R2 = b^2+b+1 (a<b) or a^2 (a>b); R3 from the tables)
RJ = {(6, 5): [6, 36, 241], (5, 4): [5, 25, 141], (3, 2): [3, 9, 31, 103], (4, 3): [4, 16, 73], (2, 3): [4, 13, 61],
      (5, 2): [5, 25, 125], (5, 3): [5, 25, 125],
      # a < b, 3-colour values from the tables (R1 = b+1, R2 = b^2+b+1): for the 4-colour a < b scan (85)
      (3, 4): [5, 21, 109, 461], (2, 5): [6, 31, 181], (3, 5): [6, 31, 186], (4, 5): [6, 31, 180],
      (7, 6): [7, 49, 379],
      (3, 1): [3, 9, 27, 81], (4, 1): [4, 16, 64, 256]}   # 11-02: a(x-y)=z, R_k = a^k known for k <= 4 (growth conjecture test, k = 5)   # R3(7,6) = a^3+(a-1)^2 (CDW22, a = b+1)


def implied(k, a, K, v, inset):
    """scaling lemma (the 'implied clauses' that made (5,3) 2.7x faster on 2026-10-24): D_d = {a*d*m : m <= K//d} is a
    copy of [1, K//d] (same equation, all its solutions are inside S).  If K//d >= R_j then D_d uses at least j+1 colours:
    for every set P of j colours, some element of D_d has a colour outside P."""
    from itertools import combinations
    out = []
    Rs = RJ.get((a, K_B[0]), [])
    for d in range(1, K + 1):
        L = K // d
        need = max([j for j, R in enumerate(Rs, 1) if L >= R] + [0])   # D_d needs >= need+1 colours
        if need == 0: break
        D = [a * d * m for m in range(1, L + 1) if a * d * m in inset]
        for P in combinations(range(k), need):
            out.append([v(x, c) for x in D for c in range(k) if c not in P])
    return out


K_B = [0]


def build(job):
    if job in _CACHE: return _CACHE[job]
    k, a, b, n, K = job.split(","); k, a, b, n = int(k), int(a), int(b), int(n); K = (n // a) if K == "all" else int(K)
    r = n % b
    S = [x for x in range(1, n + 1) if (x % a == 0 and x <= a * K) or x % b == r]
    idx = {x: i for i, x in enumerate(S)}; v = lambda x, c: k * idx[x] + c + 1
    cl = []
    for i, x in enumerate(S):
        cl.append([v(x, c) for c in range(min(k, i + 1))])
        for c in range(i + 1, k): cl.append([-v(x, c)])
    q = 1
    while b * q <= n - 1 and a * q <= n:
        d, z = b * q, a * q
        if z in idx:
            for y in S:
                if y + d > n: break
                if y + d in idx:
                    T = sorted({y, y + d, z})
                    for c in range(k): cl.append([-v(t, c) for t in T])
        q += 1
    K_B[0] = b
    imp = implied(k, a, K, v, set(S)) if K <= n // a else []
    cl += imp
    _CACHE[job] = (k, len(S), cl, v, S)
    return _CACHE[job]


CADICAL_WALL = [0.0]
HARD_WALL = [120.0]          # hard cubes: MiniSat again for this long (the 2-minute version split (6,5) quickly) before CaDiCaL


def solve_cube(arg):
    """arg = (job, cube, wall, cadw, mode); mode 'mini' = MiniSat for `wall` s; mode 'cad' = CaDiCaL only, killed after cadw s"""
    job, cube, wall = arg[:3]; cadw = arg[3] if len(arg) > 3 else 0.0; mode = arg[4] if len(arg) > 4 else "mini"
    from pysat.solvers import Solver
    k, ns, cl, v, S = build(job)
    assum = [v(S[i], int(c)) for i, c in enumerate(cube)]
    t0 = time.time()
    if mode == "mini":
        with Solver(name="minisat22", bootstrap_with=cl) as s:
            tm = threading.Timer(wall, s.interrupt); tm.start()
            res = s.solve_limited(assumptions=assum, expect_interrupt=True); tm.cancel()
        return job, cube, ("TIMEOUT" if res is None else ("SAT" if res else "UNSAT")), round(time.time() - t0, 1)
    import subprocess, tempfile
    st = "TIMEOUT"
    fd, path = tempfile.mkstemp(suffix=".cnf"); os.close(fd)
    try:
        with open(path, "w") as f:
            f.write(f"p cnf {k * ns} {len(cl) + len(assum)}\n")
            f.writelines(" ".join(map(str, c)) + " 0\n" for c in cl)
            f.writelines(f"{a_} 0\n" for a_ in assum)
        try:
            p = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "solve_one.py"), path, "cadical153"],
                               capture_output=True, text=True, timeout=cadw)
            out = p.stdout.strip()
            if out in ("SAT", "UNSAT"): st = out + "_CADICAL"
        except subprocess.TimeoutExpired:
            pass
    finally:
        try: os.remove(path)
        except OSError: pass
    return job, cube, st, round(time.time() - t0, 1)


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
        elif key == "--cadical-wall": CADICAL_WALL[0] = float(val)
        elif key == "--hard-wall": HARD_WALL[0] = float(val)
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
    # LIGHT FIRST: every cube first gets a short MiniSat run (--cube-wall).  Hard cubes: MiniSat --hard-wall (2 min), then  A cube that is not solved goes to the HARD queue
    # (row status HARD, kept on restart) and waits until all light work is done.  Hard cubes: CaDiCaL (--cadical-wall, killable;
    # adaptive: kept only while it solves >= 30% of them after 20 tries, re-tested every 50th), then split (+3 colours);
    # the children are light work again.
    Q = {j: [] for j in jobs}; H = {j: [] for j in jobs}
    for j in jobs:
        if "SAT" in st[j].values(): print(f"{j}: already SAT -> skipped", flush=True); continue
        for c in open_cubes(j):
            (H if st[j].get(c) == "HARD" else Q)[j].append((j, c, cw))
    print(f"[{datetime.now(JST):%H:%M:%S}] light {sum(len(Q[j]) for j in jobs)} / hard {sum(len(H[j]) for j in jobs)} open cubes", flush=True)
    pool = mp.Pool(W); pending = {}; dead = set(); turn = 0; last = 0.0
    ctry, cok, nhard = [0], [0], [0]
    # cost-based rule (like Concurrent Cube-and-Conquer: split only where the CDCL solver does not finish cheaply):
    #   CaDiCaL on a hard cube is worth it iff  p * T_split  >  p * t_ok + (1 - p) * W
    #   p = share of hard cubes CaDiCaL solved, t_ok = its mean time when it solved one, W = --cadical-wall (time lost on a fail),
    #   T_split = mean total CPU seconds of a split cube's whole subtree (measured on finished subtrees in this run).
    cad_ok_t = []; split_open = {}; split_cost = {}; split_done = []
    def note_time(job, cube, sec, resolved, children=0):
        # add sec to every split ancestor of cube; keep the number of open leaves below each split cube
        anc = [(job, cube[:L]) for L in range(len(cube) - 3, D - 1, -3) if (job, cube[:L]) in split_open]
        for a_ in anc: split_cost[a_] += sec
        if children:
            split_open[(job, cube)] = children; split_cost[(job, cube)] = 0.0
            for a_ in anc: split_open[a_] += children - 1
        elif resolved:
            for a_ in anc:
                split_open[a_] -= 1
                if split_open[a_] == 0: split_done.append(split_cost[a_])
    def cad_worth():
        if CADICAL_WALL[0] <= 0: return False
        if ctry[0] < 10 or len(split_done) < 5: return True             # not enough data yet: keep exploring
        p_ = cok[0] / ctry[0]; t_ok = (sum(cad_ok_t) / len(cad_ok_t)) if cad_ok_t else CADICAL_WALL[0]
        T = sum(split_done) / len(split_done)
        return p_ * T > p_ * t_ok + (1 - p_) * CADICAL_WALL[0]
    fin = {j: 0 for j in jobs}; spl = {j: 0 for j in jobs}
    try:
        while any(Q[j] or H[j] for j in jobs if j not in dead) or any(k_[0] not in dead for k_ in pending):   # v-watchdog: do not wait for stopped jobs
            try:
                from grid_rado import free_mem_gb
                fm = free_mem_gb()
            except Exception:
                fm = None
            room = not (fm is not None and fm < 4.0 and pending)
            while room and len(pending) < W:
                lj = [j for j in jobs if j not in dead and Q[j]]
                if lj:
                    j = lj[turn % len(lj)]; turn += 1; item = Q[j].pop(0)
                    pending[(j, item[1])] = (pool.apply_async(solve_cube, ((j, item[1], cw, 0.0, "mini"),)), time.time(), "mini"); continue
                hj = [j for j in jobs if j not in dead and H[j]]
                if not hj: break
                j = hj[turn % len(hj)]; turn += 1; item = H[j].pop(0)
                stage = item[3] if len(item) > 3 else 1
                if stage == 1 and HARD_WALL[0] > 0:          # stage 1: MiniSat for --hard-wall
                    pending[(j, item[1])] = (pool.apply_async(solve_cube, ((j, item[1], HARD_WALL[0], 0.0, "mini"),)), time.time(), "mini2"); continue
                nhard[0] += 1
                use = cad_worth() or (CADICAL_WALL[0] > 0 and nhard[0] % 50 == 0)    # every 50th: re-measure
                if use:                                       # stage 2: CaDiCaL
                    pending[(j, item[1])] = (pool.apply_async(solve_cube, ((j, item[1], cw, CADICAL_WALL[0], "cad"),)), time.time(), "cad")
                else:                                     # split at once; children are light work
                    row(j, item[1], "SPLIT", 0.0); spl[j] += 1; k = int(j.split(",")[0])
                    ch = firstfit(item[1], 3, k); note_time(j, item[1], 0.0, False, len(ch))
                    Q[j] = [(j, c, cw) for c in ch] + Q[j]
            time.sleep(0.5)
            # watchdog (2026-10-31): a MiniSat run that ignores its interrupt (seen in 85/86, 0% CPU for hours) or a stopped job's
            # leftover: after its limit + 120 s it is recorded as TIMEOUT (it then goes on as a hard cube / split) and the pool is restarted
            lim = lambda m_: (cw if m_ == "mini" else HARD_WALL[0] if m_ == "mini2" else CADICAL_WALL[0] + cw) + 120
            hung = [k_ for k_, (ar, ts, m_) in pending.items() if not ar.ready() and (k_[0] in dead or time.time() - ts > lim(m_))]
            if hung:
                pool.terminate(); pool = mp.Pool(W)
                for k_ in hung:
                    ar, ts, m_ = pending.pop(k_); job, cube = k_
                    if job in dead: continue
                    print(f"   {job}: cube {cube} gave no answer after {time.time() - ts:.0f}s ({m_}) -> treated as TIMEOUT (watchdog, pool restarted)", flush=True)
                    if m_ == "mini": row(job, cube, "HARD", round(time.time() - ts, 1)); H[job].append((job, cube, cw, 1))
                    elif m_ == "mini2": H[job].insert(0, (job, cube, cw, 2))
                    else:
                        row(job, cube, "SPLIT", round(time.time() - ts, 1)); spl[job] += 1; k = int(job.split(",")[0])
                        ch = firstfit(cube, 3, k); note_time(job, cube, 0.0, False, len(ch)); Q[job] = [(job, c, cw) for c in ch] + Q[job]
                for k_ in list(pending):                       # the others were killed with the pool: start them again
                    ar, ts, m_ = pending[k_]; job, cube = k_
                    if job in dead: del pending[k_]; continue
                    if m_ == "mini": a_ = (job, cube, cw, 0.0, "mini")
                    elif m_ == "mini2": a_ = (job, cube, HARD_WALL[0], 0.0, "mini")
                    else: a_ = (job, cube, cw, CADICAL_WALL[0], "cad")
                    pending[k_] = (pool.apply_async(solve_cube, (a_,)), time.time(), m_)
            for key, (ar, ts, mode) in list(pending.items()):
                if not ar.ready(): continue
                del pending[key]; job, cube, res, sec = ar.get(); nfin += 1; fin[job] += 1
                if mode == "cad":
                    ctry[0] += 1; cok[0] += res.endswith("_CADICAL")
                    if res.endswith("_CADICAL"): cad_ok_t.append(sec)
                    if res.endswith("_CADICAL"):
                        print(f"   {job}: hard cube {cube} solved by CaDiCaL: {res[:-8]} ({sec}s)", flush=True); res = res[:-8]
                if res == "TIMEOUT":
                    if mode == "mini":
                        row(job, cube, "HARD", sec); H[job].append((job, cube, cw, 1))
                    elif mode == "mini2":
                        note_time(job, cube, sec, False)
                        H[job].insert(0, (job, cube, cw, 2))       # next: CaDiCaL (or split)
                    else:
                        row(job, cube, "SPLIT", sec); spl[job] += 1; k = int(job.split(",")[0])
                        ch = firstfit(cube, 3, k); note_time(job, cube, sec, False, len(ch))
                        Q[job] = [(job, c, cw) for c in ch] + Q[job]
                    if mode == "mini": note_time(job, cube, sec, False)
                else:
                    note_time(job, cube, sec, True)
                    row(job, cube, res, sec)
                    if res == "SAT":
                        print(f"   {job}: cube {cube} SAT -> S is colourable, job stopped", flush=True); dead.add(job); Q[job] = []; H[job] = []
                if job not in dead and not Q[job] and not H[job] and not any(p[0] == job for p in pending):
                    print(f"*** {job}: ALL cubes UNSAT -> S is not colourable -> [1,n] is not colourable", flush=True)
            if time.time() - last > 60:
                last = time.time(); el = time.time() - t0; parts = []
                for j in jobs:
                    if j in dead: parts.append(f"{j}: stopped (SAT)"); continue
                    lq = len(Q[j]) + sum(1 for p in pending if p[0] == j and pending[p][2] == "mini")
                    hq = len(H[j]) + sum(1 for p in pending if p[0] == j and pending[p][2] in ("cad", "mini2"))
                    parts.append(f"{j}: done {fin[j]} (split {spl[j]}), light open {lq}, hard waiting {hq}")
                rate = nfin / el if el else 0
                print(f"[{datetime.now(JST):%H:%M:%S}] elapsed {el/60:.0f} min | " + " | ".join(parts)
                      + f" | light ETA ~{(sum(len(Q[j]) for j in jobs) / rate / 60) if rate else float('nan'):.0f} min"
                      + (f" | CaDiCaL solved {cok[0]}/{ctry[0]} hard cubes, split subtrees finished {len(split_done)}"
                         + (f" (mean {sum(split_done)/len(split_done):.0f} CPU s)" if split_done else "")
                         + f" -> CaDiCaL {'ON' if cad_worth() else 'OFF (split at once)'}" if CADICAL_WALL[0] > 0 else ""), flush=True)
    except KeyboardInterrupt:
        print("Ctrl+C: stopped (finished cubes are saved)")
    finally:
        pool.terminate()
    print(f"done ({OUT})")


if __name__ == "__main__":
    main()

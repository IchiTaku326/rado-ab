# -*- coding: utf-8 -*-
r"""DRAT check of the SMALL-SET (S) upper bounds (run inside WSL / Linux, like 9_verify_proofs.bat / verify_proofs.py).
For every task: write the CNF of S, let CaDiCaL write a DRAT proof, let drat-trim check it -> VERIFIED.
  * The CNF of S is a SUBSET of the clauses of the full CNF of [1,n] (only solutions whose x,y,z are all in S) plus colour
    symmetry breaking (3 colours: the smallest element of S has colour 0; k colours: the i-th element of S uses colours 0..i,
    "first fit"; both are w.l.o.g. by permuting colours).  So S UNSAT  =>  [1,n] not colourable.
  * Every clause is re-checked against the equation a(x-y) = bz before writing (independent of the generator).
Tasks:
  (A) 4 colours, R4(5(x-y)=4z) = 741: every leaf cube of results\subset_cubes.csv (job 4,5,4,741,141) with the cube as unit
      clauses; plus a completeness check (the leaves must be exactly the first-fit tree: depth-7 roots, SPLIT nodes +3).
  (B) 3 colours: every UNSAT row of results\subset_K_bb1.csv with a < b <= --bmax (S with K = b^2+b+1).
Resumable: results\proofcheck_subset.csv (one row per task, flush+fsync); VERIFIED rows are skipped.  Memory gate (WSL has
its own memory limit): a task starts only if MemAvailable - estimate >= 3 GB.  Per-task wall limit (TIMEOUT rows are retried
on the next run).  Progress + ETA every minute.  Ctrl+C is safe.
Run (inside WSL, from the project folder): python3 tools/verify_subset.py --workers 11 --bmax 41"""
import argparse, csv, os, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
TRY = int(os.environ.get("CAKE_HEAP_TRY", "0") or 0)   # 11-02 15:40: try the big cake_lpr with a SMALLER heap first (MB)
TRYST = {"state": "probe" if TRY else "off", "fails": 0, "ok": 0}
PEAK = {}            # 11-02: task key -> peak memory (GB) of its biggest child process (cadical / cake_lpr), measured
JST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "results", "proofcheck_subset.csv")
now = lambda: datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")


def subset(a, b, n, K):
    r = n % b
    return [x for x in range(1, n + 1) if (x % a == 0 and x <= a * K) or x % b == r]


def cnf_lines(k, a, b, n, K, cube):
    S = subset(a, b, n, K); idx = {x: i for i, x in enumerate(S)}; v = lambda x, c: k * idx[x] + c + 1
    out = []
    for i, x in enumerate(S):
        out.append([v(x, c) for c in range(k)])                              # at least one colour (as in the full CNF)
        if k == 3:
            if i == 0: out.append([v(x, 0)])                                 # symmetry: smallest element colour 0
        else:
            for c in range(i + 1, k): out.append([-v(x, c)])                 # first fit (i-th element: colours 0..i)
    q = 1
    while b * q <= n - 1 and a * q <= n:
        d, z = b * q, a * q
        if z in idx:
            for y in S:
                if y + d > n: break
                if y + d in idx:
                    x = y + d
                    assert a * (x - y) == b * z and 1 <= y < x <= n and z <= n     # independent check of every solution
                    T = sorted({y, x, z})
                    for c in range(k): out.append([-v(t, c) for t in T])
        q += 1
    for i, c in enumerate(cube):
        out.append([v(S[i], int(c))])
    return k * len(S), out


def mem_avail_gb():
    try:
        for l in open("/proc/meminfo"):
            if l.startswith("MemAvailable:"): return int(l.split()[1]) / 2 ** 20
    except Exception:
        return None


def run_peak(cmd, timeout):
    """11-02: like subprocess.run(..., timeout) but also measures the child's peak memory (VmHWM, GB)."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    out = []; th = threading.Thread(target=lambda: out.append(p.stdout.read()), daemon=True); th.start()
    t0 = time.time(); peak = 0
    while p.poll() is None:
        try:
            for l in open(f"/proc/{p.pid}/status"):
                if l.startswith("VmHWM:"): peak = max(peak, int(l.split()[1]))
        except Exception:
            pass
        if time.time() - t0 > timeout:
            p.kill(); p.wait(); th.join(5); raise subprocess.TimeoutExpired(cmd, timeout)
        time.sleep(0.5)
    th.join(5)
    return "".join(out), peak / 1048576.0


def run_task(task, binr, wall):
    key, k, a, b, n, K, cube = task
    t0 = time.time(); d = tempfile.mkdtemp(prefix="vs_")
    try:
        nv, cl = cnf_lines(k, a, b, n, K, cube)
        cnf = os.path.join(d, "s.cnf"); prf = os.path.join(d, "s.drat")
        with open(cnf, "w") as f:
            f.write(f"p cnf {nv} {len(cl)}\n"); f.writelines(" ".join(map(str, c)) + " 0\n" for c in cl)
        ncl = len(cl); del cl; cl = range(ncl)        # 11-02: free the Python clause list (GBs) before the solver runs
        pk = 0.0
        lrat = os.path.exists(os.path.join(binr, "lrat-check-ok"))
        try:
            cmd = [os.path.join(binr, "cadical"), "-q"] + (["--lrat", "--no-binary"] if lrat else []) + [cnf, prf]
            so, g = run_peak(cmd, wall); pk = max(pk, g)
        except subprocess.TimeoutExpired:
            return key, "TIMEOUT_SOLVE", len(cl), 0, round(time.time() - t0, 1)
        st = [l for l in so.splitlines() if l.startswith("s ")]
        if not (st and "UNSATISFIABLE" in st[0]):
            return key, "SOLVER_" + (st[0][2:].replace(" ", "_") if st else "NONE"), len(cl), 0, round(time.time() - t0, 1)
        pb = os.path.getsize(prf)
        try:
            if lrat:   # LRAT (hints in the proof): linear-time check, 3-5x faster than drat-trim's backward check
                q = subprocess.run([os.path.join(binr, "lrat-check"), cnf, prf], capture_output=True, text=True, timeout=wall + 60)
                res = "VERIFIED" if "c VERIFIED" in q.stdout else "NOTVERIFIED"
                if res == "VERIFIED" and os.path.exists(os.path.join(binr, "cake-ok")):
                    # second, FORMALLY VERIFIED checker (cake_lpr, CakeML/HOL4; heap 700 MB compiled in). If it runs out of
                    # memory on a big proof, the lrat-check result stays.
                    try:
                        cb = "cake_lpr_big" if (key.startswith("k3") and os.path.exists(os.path.join(binr, "cake_lpr_big"))) else "cake_lpr"
                        use_try = bool(TRY) and cb == "cake_lpr_big" and TRYST["state"] in ("probe", "on")
                        cmd = [os.path.join(binr, cb)] + ([f"--CML_HEAP_SIZE={TRY}"] if use_try else []) + [cnf, prf]
                        c2o, g = run_peak(cmd, wall + 60); pk = max(pk, g)
                        if use_try:
                            if "s VERIFIED UNSAT" in c2o:
                                TRYST["ok"] += 1
                                if TRYST["state"] == "probe":
                                    TRYST["state"] = "on"; print(f"[{now()}] heap {TRY} MB is enough for {key}: checking in parallel from now on", flush=True)
                            elif TRYST["state"] == "probe":      # the probe runs alone: switch off and redo with the full heap
                                TRYST["state"] = "off"; print(f"[{now()}] heap {TRY} MB is NOT enough ({key}): one at a time with the full heap", flush=True)
                                c2o, g = run_peak([os.path.join(binr, cb), cnf, prf], wall + 60); pk = max(pk, g)
                            else:                                # parallel phase: leave it lrat-only, the next (full-heap) pass redoes it
                                TRYST["fails"] += 1
                        if "s VERIFIED UNSAT" in c2o: res = "VERIFIED_CAKE"
                    except subprocess.TimeoutExpired:
                        pass
            else:
                q = subprocess.run([os.path.join(binr, "drat-trim"), cnf, prf, "-t", str(int(wall))], capture_output=True, text=True, timeout=wall + 60)
                res = "VERIFIED" if "s VERIFIED" in q.stdout else "NOTVERIFIED"
        except subprocess.TimeoutExpired:
            res = "TIMEOUT_CHECK"
        PEAK[key] = pk
        return key, res, len(cl), pb, round(time.time() - t0, 1)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def firstfit(prefix, extra, k):
    out = [prefix]
    for _ in range(extra):
        nxt = []
        for p_ in out:
            m = max((int(c) for c in p_), default=-1)
            nxt += [p_ + str(c) for c in range(min(k, m + 2))]
        out = nxt
    return out


def tasks_A(extra=()):
    """leaf cubes of the 4-colour subset searches: R4(5,4)=741 and R4(6,5)=1501 (+ --cube-jobs, 2026-11-01: the new 4-colour
    upper bounds of 86; a job without a complete cube tree in subset_cubes.csv is checked as ONE task on the whole S)"""
    allt, complete = [], True
    jl = [("4,5,4,741,141", "k4_5_4_741"), ("4,6,5,1501,241", "k4_6_5_1501")] if not extra else []
    for job in extra:
        k_, a_, b_, n_, K_ = job.split(","); jl.append((job, f"k{k_}_{a_}_{b_}_{n_}"))
    for job, tag in jl:
        k, a, b, n, K = [int(t) for t in job.split(",")]
        st = {}
        f = os.path.join(ROOT, "results", "subset_cubes.csv")
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["job"] == job: st[r["cube"]] = r["status"]
        leaves, stack, missing = [], firstfit("0", 6, 4), []
        while stack:
            c = stack.pop()
            if st.get(c) == "SPLIT": stack += firstfit(c, 3, 4)
            elif st.get(c) == "UNSAT": leaves.append(c)
            else: missing.append(c)
        if extra and not leaves:                                   # solved without cubes (quick MiniSat UNSAT): whole S
            print(f"[{now()}] (A) R{k}({a},{b})={n}: no cube tree -> one task on the whole S", flush=True)
            allt.append((f"{tag}_whole", k, a, b, n, K, "")); continue
        print(f"[{now()}] (A) R{k}({a},{b})={n}: {len(leaves)} leaf cubes, tree complete: {'YES' if not missing else 'NO, missing ' + str(len(missing))}", flush=True)
        complete = complete and not missing
        allt += [(f"{tag}_cube{c}", k, a, b, n, K, c) for c in leaves]
    return allt, complete


def tasks_B(bmax, bmin=0, formula=0):
    """3 colours: UNSAT rows of subset_K_bb1.csv, and (formula=1, 2026-10-31) every cell 2 <= a < b, gcd = 1 at n = N(a,b) =
    min(a*m', M+ab+1) (the conjectured value; the lower bound R3 >= N is a theorem).  Before this, only the subset_K_bb1 rows were
    checked: the cells outside formula 1 whose upper bound came from s_min (results\\s_min3.csv) were NOT DRAT-checked."""
    f = os.path.join(ROOT, "results", "subset_K_bb1.csv"); seen = set(); out = []
    for r in csv.DictReader(open(f, encoding="utf-8")):
        a, b, n = int(r["a"]), int(r["b"]), int(r["n"])
        if r["result"] == "UNSAT" and a < b and bmin <= b <= bmax and (a, b, n) not in seen:
            seen.add((a, b, n)); out.append((f"k3_{a}_{b}_{n}", 3, a, b, n, b * b + b + 1, ""))
    if formula:
        from math import gcd
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from conj_jobs import N
        for b in range(max(bmin, 3), bmax + 1):
            for a in range(2, b):
                if gcd(a, b) != 1 or (a, b) in ((2, 3), (2, 5)): continue      # (2,3), (2,5): value is not N (rows above)
                n = N(a, b)
                if (a, b, n) not in seen:
                    seen.add((a, b, n)); out.append((f"k3_{a}_{b}_{n}", 3, a, b, n, b * b + b + 1, ""))
    out.sort(key=lambda t: (t[3], t[2]))
    print(f"[{now()}] (B) 3 colours, {bmin} <= b <= {bmax}{' (all cells at N(a,b))' if formula else ''}: {len(out)} cells", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=11); ap.add_argument("--bmax", type=int, default=41)
    ap.add_argument("--wall", type=float, default=3600)
    ap.add_argument("--bmin", type=int, default=0); ap.add_argument("--formula", type=int, default=0, help="1: all 3-colour cells at N(a,b)")
    ap.add_argument("--only-b", type=int, default=0, help="1: only the 3-colour tasks (B)")
    ap.add_argument("--cube-jobs", default="", help="k,a,b,n,K jobs (space separated) whose subset_cubes leaves are checked as (A); with this, B is skipped")
    ap.add_argument("--cake-recheck", type=int, default=0, help="1: re-run tasks that are only VERIFIED (not VERIFIED_CAKE) to get the cake_lpr check")
    a = ap.parse_args()
    binr = os.path.join(tempfile.gettempdir(), "satbin"); os.makedirs(binr, exist_ok=True)
    for nm in ("cadical", "drat-trim"):                                     # /mnt/<drive> binaries are often not executable
        shutil.copy(os.path.join(ROOT, "bin_linux", nm), os.path.join(binr, nm)); os.chmod(os.path.join(binr, nm), 0o755)
    # LRAT checker (lrat-check, from the drat-trim sources): build it here with gcc (matches this Linux), else use the copy in
    # bin_linux; test it on a tiny UNSAT formula.  If anything fails, the DRAT + drat-trim path is used (as for 226).
    ok = False
    src = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(ROOT, "solvers", "drat-trim")) for f in fs if f == "lrat-check.c"]
    try:
        built = False
        try:
            built = bool(src) and subprocess.run(["gcc", "-O2", "-o", os.path.join(binr, "lrat-check"), src[0]], capture_output=True).returncode == 0
        except Exception:
            built = False                                                  # no gcc in this Linux
        if not built:                                                      # static binary (runs on any Linux)
            shutil.copy(os.path.join(ROOT, "bin_linux", "lrat-check"), os.path.join(binr, "lrat-check"))
        os.chmod(os.path.join(binr, "lrat-check"), 0o755)
        tc = os.path.join(binr, "t.cnf"); tp = os.path.join(binr, "t.lrat")
        open(tc, "w").write("p cnf 2 4\n1 2 0\n-1 2 0\n1 -2 0\n-1 -2 0\n")
        subprocess.run([os.path.join(binr, "cadical"), "-q", "--lrat", "--no-binary", tc, tp], capture_output=True, timeout=60)
        ok = "c VERIFIED" in subprocess.run([os.path.join(binr, "lrat-check"), tc, tp], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        ok = False
    cake = False
    try:
        shutil.copy(os.path.join(ROOT, "bin_linux", "cake_lpr"), os.path.join(binr, "cake_lpr")); os.chmod(os.path.join(binr, "cake_lpr"), 0o755)
        big = os.environ.get("CAKE_BIG", "cake_lpr_big")      # 11-02: CAKE_BIG=cake_lpr_14g (heap 14 GB) for b = 57..60
        if os.path.exists(os.path.join(ROOT, "bin_linux", big)):       # heap 4 GB (or more) for the big 3-colour proofs
            shutil.copy(os.path.join(ROOT, "bin_linux", big), os.path.join(binr, "cake_lpr_big")); os.chmod(os.path.join(binr, "cake_lpr_big"), 0o755)
            print(f"[{now()}] big proofs: {big}", flush=True)
        cake = ok and "s VERIFIED UNSAT" in subprocess.run([os.path.join(binr, "cake_lpr"), tc, tp], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        cake = False
    if cake: open(os.path.join(binr, "cake-ok"), "w").write("ok")
    elif os.path.exists(os.path.join(binr, "cake-ok")): os.remove(os.path.join(binr, "cake-ok"))
    print(f"[{now()}] formally verified checker cake_lpr: {'ON (result VERIFIED_CAKE)' if cake else 'not available'}", flush=True)
    if ok: open(os.path.join(binr, "lrat-check-ok"), "w").write("ok")
    elif os.path.exists(os.path.join(binr, "lrat-check-ok")): os.remove(os.path.join(binr, "lrat-check-ok"))
    print(f"[{now()}] proof format: {'LRAT (cadical --lrat) checked by lrat-check' if ok else 'DRAT checked by drat-trim'}", flush=True)
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            if r["result"] == "VERIFIED_CAKE" or (r["result"] == "VERIFIED" and not a.cake_recheck): done.add(r["task"])
    ex = a.cube_jobs.split()
    tA, completeA = tasks_A(ex); tB = [] if ex else tasks_B(a.bmax, a.bmin, a.formula)
    order = ([t for t in tA if t[0].startswith("k4_5_4")] + tB + [t for t in tA if not t[0].startswith("k4_5_4")]) if not ex else tA
    if a.only_b: order = tB
    todo = [t for t in order if t[0] not in done]
    print(f"[{now()}] {len(todo)} tasks to check ({len(done)} already VERIFIED), {a.workers} workers, wall {a.wall/60:.0f} min per task", flush=True)
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "task", "result", "clauses", "proof_bytes", "seconds"]); fh.flush()
    est = lambda t: 2.0 + 4e-7 * (t[4] / t[3]) ** 2 * (1 if t[1] == 3 else 0) * 1.0   # GB, rough (CaDiCaL / cake_lpr + 1 GB margin)
    if os.environ.get("CAKE_BIG", "cake_lpr_big") != "cake_lpr_big":    # 11-02: the big cake_lpr allocates its whole heap at start
        _e0 = est; seen_pk = []                                        # 11-02: (peak GB, (n/b)^2) of finished 3-colour tasks
        def est(t):
            if t[1] != 3: return _e0(t)
            if TRYST["state"] == "probe": return 1e9                    # the probe task runs alone
            if TRYST["state"] == "on": return TRY / 1024 + 2.0            # fixed heap + margin (cadical runs before cake)
            if not seen_pk: return max(_e0(t), 17.0)                   # nothing measured yet: one at a time
            r = max(pk / s for pk, s in seen_pk)                       # the heap is touched lazily: real use is measured
            return max(2.0, r * (t[4] / t[3]) ** 2 * 1.3 + 1.5)
    else:
        seen_pk = []
    m0 = mem_avail_gb(); budget = (m0 - 3.0) if m0 is not None else 12.0   # 11-01: running tasks' estimates must fit (tasks grow after start)
    print(f"[{now()}] WSL memory available {m0 if m0 is None else round(m0, 1)} GB -> budget for running tasks {budget:.1f} GB", flush=True)
    t0 = time.time(); fin = 0; bad = 0; last = 0.0; running = {}; tinfo = {}
    mfh = open(os.path.join(ROOT, "results", "proofcheck_mem.csv"), "a", encoding="utf-8")
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        queue = list(todo)
        try:
            while queue or running:
                while queue and len(running) < a.workers:
                    m = mem_avail_gb(); e = est(queue[0])
                    if m is not None and running and m - e < 3.0: break
                    if running and sum(e_ for _, e_ in running.values()) + e > budget: break
                    t = queue.pop(0); running[t[0]] = (ex.submit(run_task, t, binr, a.wall), e); tinfo[t[0]] = t
                time.sleep(1)
                for k_, (fu, e) in list(running.items()):
                    if not fu.done(): continue
                    del running[k_]; key, res, ncl, pb, sec = fu.result(); fin += 1; bad += not res.startswith("VERIFIED")
                    w.writerow([now(), key, res, ncl, pb, sec]); fh.flush(); os.fsync(fh.fileno())
                    tt = tinfo.pop(key, None); g = PEAK.pop(key, 0.0)
                    if tt and g > 0 and tt[1] == 3 and res.startswith("VERIFIED"): seen_pk.append((g, (tt[4] / tt[3]) ** 2))
                    mfh.write(f"{now()},{key},{res},{g:.2f}\n"); mfh.flush()
                    if not res.startswith("VERIFIED"): print(f"[{now()}] {key}: {res} ({sec}s)", flush=True)
                if time.time() - last > 60 and fin:
                    last = time.time(); el = time.time() - t0
                    print(f"[{now()}] checked {fin}/{len(todo)} (not verified {bad}), running {len(running)} (estimated {sum(e_ for _, e_ in running.values()):.0f} GB of {budget:.0f}), elapsed {el/60:.0f} min, "
                          f"ETA about {el/fin*(len(todo)-fin)/60:.0f} min", flush=True)
        except KeyboardInterrupt:
            print("Ctrl+C: stopping (finished rows are kept)"); ex.shutdown(wait=False, cancel_futures=True); return
    ver = set(r["task"] for r in csv.DictReader(open(OUT, encoding="utf-8")) if r["result"].startswith("VERIFIED"))
    okA = sum(1 for t in tA if t[0] in ver); okB = sum(1 for t in tB if t[0] in ver)
    ok54 = sum(1 for t in tA if t[0] in ver and t[0].startswith("k4_5_4")); n54 = sum(1 for t in tA if t[0].startswith("k4_5_4"))
    ok65 = sum(1 for t in tA if t[0] in ver and t[0].startswith("k4_6_5")); n65 = sum(1 for t in tA if t[0].startswith("k4_6_5"))
    if TRY: print(f"[{now()}] small heap {TRY} MB: {TRYST['ok']} verified, {TRYST['fails']} need the full heap (state {TRYST['state']})", flush=True)
    per = {}                                                   # 11-03: one count per job (also the --cube-jobs ones)
    for t in tA:
        tag = t[0].split("_cube")[0].split("_whole")[0]; c = per.setdefault(tag, [0, 0]); c[1] += 1; c[0] += t[0] in ver
    jobs = "; ".join(f"{tag}: {c[0]}/{c[1]} VERIFIED" for tag, c in per.items())
    line = (f"[{now()}] (A) tree complete {'YES' if completeA else 'NO'}; R4(5,4)=741: {ok54}/{n54} cubes VERIFIED; R4(6,5)=1501: {ok65}/{n65} cubes VERIFIED | "
            f"(B) 3 colours b <= {a.bmax}: {okB}/{len(tB)} cells VERIFIED | per job: {jobs if jobs else '-'}")
    print(line); open(os.path.join(ROOT, "results", "proofcheck_subset_FINAL.txt"), "a", encoding="utf-8").write(line + "\n")


if __name__ == "__main__":
    main()

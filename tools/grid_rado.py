# -*- coding: utf-8 -*-
r"""
Grid of Rado numbers R_k(a(x-y)=bz) for gcd(a,b)=1, 1<=a,b<=N, k=1..K, computed by SAT.
Looking for patterns (especially b>a, where no formula is known to us) and checking known formulas.

Design (same rules as the other tools):
  * append-only decision log  results/rado_grid/decisions.csv : one row per SAT call
        jst_time,a,b,k,n,status(SAT|UNSAT|TIMEOUT),seconds,limit_s,source
    flush+fsync on every row; JST times.  Resume = run again (everything is read back from the log).
  * for each (a,b,k): gallop n=4,8,16.. until UNSAT, then bisect; colourability is monotone in n.
  * passes: a TIMEOUT decision is retried in the next pass with a 4x longer limit.
  * `report` writes results/rado_grid/TABLES.md (tables with exact values / bounds, formula checks, notes).
PowerShell:
  python tools\grid_rado.py run --N 12 --K 4 --workers 11 --backend pysat --limit 600
  python tools\grid_rado.py report
"""
import argparse, csv, math, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
FIELDS = ["jst_time", "a", "b", "k", "n", "status", "seconds", "limit_s", "source"]
HERE = os.path.dirname(os.path.abspath(__file__))
LOCK = threading.Lock()
ACTIVE = set()
STARTED = {}          # SAT process -> start time (for the hard memory cap)
RUNNING = {}          # SAT process -> (a, b, k, n, start time)  for the progress lines
MEMKILLED = set()     # SAT processes killed by the hard memory cap (retried, nothing written)
PRESSURE_UNTIL = [0.0]
STOP = threading.Event()


def now(): return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")


def kill_tree(p):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal
            try: os.killpg(p.pid, signal.SIGKILL)
            except Exception: p.kill()
    except Exception:
        pass


def load(path):
    rows = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    return rows


def append(path, row):
    with LOCK:
        new = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new: w.writeheader()
            w.writerow({k: row.get(k, "") for k in FIELDS})
            f.flush(); os.fsync(f.fileno())


def state(rows, a, b, k):
    """-> (lo, hi, timeouts): lo = largest n known colourable (0 if none), hi = smallest n known not colourable (None)"""
    lo, hi, to = 0, None, {}
    for r in rows:
        if (int(r["a"]), int(r["b"]), int(r["k"])) != (a, b, k): continue
        n = int(r["n"])
        if r["status"] == "SAT": lo = max(lo, n)
        elif r["status"] == "UNSAT": hi = n if hi is None else min(hi, n)
        else: to[n] = max(to.get(n, 0), float(r["limit_s"] or 0))
    return lo, hi, to


def cube_root(args):
    """folder for the working files of the cube searches (many small writes: put it on an SSD with --cube-root)"""
    return getattr(args, "cube_root", None) or os.path.join(args.outdir, "cubes")


def decide_cube(args, a, b, k, n, cube_workers):
    """long calls: split into cubes (cube_search.py). Every finished cube is saved, so Ctrl+C / a crash loses at most
    the few cubes in flight. returns SAT / UNSAT / INTERRUPTED"""
    cdir = os.path.join(cube_root(args), f"a{a}_b{b}_k{k}_n{n}")
    os.makedirs(cdir, exist_ok=True)
    cmd = [sys.executable, os.path.join(HERE, "cube_search.py"), "--a", str(a), "--b", str(b), "--k", str(k), "--n", str(n),
           "--depth", str(args.cube_depth), "--workers", str(cube_workers), "--backend", args.backend, "--bin", args.bin,
           "--budget", "20000", "--split", "3", "--log-minutes", "30", "--outdir", cdir] + (["--implied", "1"] if getattr(args, "implied", 0) else [])
    t0 = time.time()
    kw = {"start_new_session": True} if os.name != "nt" else {}
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    ACTIVE.add(p)
    try:
        while p.poll() is None:
            if STOP.is_set():
                kill_tree(p); p.wait(); return "INTERRUPTED", time.time() - t0
            time.sleep(2)
    finally:
        ACTIVE.discard(p)
    if any(f.startswith("cert_") and f.endswith(".json") for f in os.listdir(cdir)):
        return "SAT", time.time() - t0
    fin = os.path.join(cdir, "FINAL.txt")
    if os.path.exists(fin) and "all_unsat=YES" in open(fin, encoding="utf-8").read():
        return "UNSAT", time.time() - t0
    return "INTERRUPTED", time.time() - t0


def cube_progress(args, cells=None):
    """-> [(name, unsat_cubes, total_cubes)] for the open cube searches of the cells of this run (cells = set of (a,b,k))"""
    out = []
    base = cube_root(args)
    if not os.path.isdir(base): return out
    sys.path.insert(0, HERE)
    import cube_search as cs
    for name in sorted(os.listdir(base)):
        try:
            q = dict((x[0], int(x[1:])) for x in name.split("_"))
            if cells is not None and (q["a"], q["b"], q["k"]) not in cells: continue
            total = len(cs.enum_cubes(q["a"], q["b"], q["k"], args.cube_depth))
            dd = os.path.join(base, name)
            done, _u = cs.done_cubes(dd)
            u = sum(1 for x in done.values() if x == "UNSAT")
            if u < total and not any(f.startswith("cert_") for f in os.listdir(dd)):   # only decisions still open
                out.append((name, u, total))
        except Exception:
            pass
    return out


# ---------- memory gate (2026-10-26): one SAT call (CaDiCaL) needs about 150 bytes per clause; clauses ~ k*n^2/(2*b/g) ----------
# measured: n~19000, b=25, k=3 -> ~2.5 GB; n~31700 -> ~7 GB (memory ~ n^2).  The ledger below admits a new SAT process only if the
# estimated memory of all running ones + the new one stays under --mem-gb, and never starts one while Windows has < 3 GB free.
MEM_COND = threading.Condition()
MEM_USED = [0.0]
MEM_BUDGET = [0.0]
MEM_FREE_MIN = 6.0     # 2026-10-28: real use grows while a run is going (2-3 runs at n~40000 reached 26.4/31.9 GB)


def est_mem_gb(a, b, k, n):
    g = math.gcd(a, b)
    clauses = k * n * n / (2.0 * max(1, b // g)) + 4 * n * k
    return clauses * 150 / 1e9 + 0.15


def free_mem_gb():
    """physical memory available right now (GB); None if unknown"""
    try:
        if os.name == "nt":
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                            ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                            ("ae", ctypes.c_ulonglong)]
            m = MS(); m.l = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ap / 2 ** 30
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable:"): return int(line.split()[1]) / 2 ** 20
    except Exception:
        return None
    return None


def mem_acquire(need, what):
    if MEM_BUDGET[0] <= 0: return 0.0
    if need > MEM_BUDGET[0]:
        print(f"[{now()} JST] memory gate: {what} SKIPPED (needs ~{need:.1f} GB > budget {MEM_BUDGET[0]:.0f} GB)", flush=True)
        return None
    first = True
    with MEM_COND:
        while True:
            fm = free_mem_gb()
            ok_budget = MEM_USED[0] == 0 or MEM_USED[0] + need <= MEM_BUDGET[0]
            ok_free = fm is None or fm >= (MEM_FREE_MIN + (8.0 if time.time() < PRESSURE_UNTIL[0] else 0.0))
            if ok_budget and ok_free: break
            if first:
                print(f"[{now()} JST] memory gate: {what} waits (needs ~{need:.1f} GB, running {MEM_USED[0]:.1f}/{MEM_BUDGET[0]:.0f} GB, free {fm if fm is None else round(fm, 1)} GB)", flush=True)
                first = False
            if STOP.is_set(): break
            MEM_COND.wait(10)
        MEM_USED[0] += need
    return need


def mem_release(need):
    if need <= 0: return
    with MEM_COND:
        MEM_USED[0] = max(0.0, MEM_USED[0] - need)
        MEM_COND.notify_all()


def mult_probes(a, b, k, lo, hi, m):
    """3 colours, 2<=a<b, outside formula 1: R3 was a multiple of a in all 68 known cells (2026-10-26, conjecture).
    Search only among multiples of a (about log2(a) fewer SAT calls), then test a*j-1 once.  Always correct: if R is not a
    multiple of a, the last test shows it (a*j-1 UNSAT) and the normal bisection takes over."""
    if not (k == 3 and 2 <= a < b and b >= 7): return None
    if a <= int(0.618 * b + 0.73): return None
    jl, jh = lo // a + 1, (hi - 1) // a                      # multiples a*j with lo < a*j < hi
    if jl > jh:
        return [hi - 1] if (hi % a == 0 and lo < hi - 1) else None
    js = sorted({jl + (jh - jl) * i // (m + 1) for i in range(1, m + 1)} | ({jl} if jl == jh else set()))
    return [a * j for j in js if lo < a * j < hi] or None


def decide(args, a, b, k, n, limit, hard=False, cube_workers=1):
    """one SAT call in a child process (killable). returns status, seconds"""
    if hard:
        return decide_cube(args, a, b, k, n, cube_workers)
    if SEM is not None:                  # at most --workers SAT processes run at the same time (several probes per cell are possible)
        with SEM:
            need = mem_acquire(est_mem_gb(a, b, k, n) * (0.4 if getattr(args, "lazy", 0) else 1.0) * (1.0 if getattr(args, "sat_solver", "cadical153").startswith("cadical") else 0.3), f"({a},{b},k={k}) n={n}")
            if need is None:
                return "ERROR", 0.0                       # too big for the budget: nothing is written, the cell waits
            try:
                return _decide_proc(args, a, b, k, n, limit)
            finally:
                mem_release(need)
    return _decide_proc(args, a, b, k, n, limit)


def _decide_proc(args, a, b, k, n, limit):
    cmd = [sys.executable, os.path.abspath(__file__), "decide", "--a", str(a), "--b", str(b), "--k", str(k), "--n", str(n),
           "--backend", args.backend, "--bin", args.bin, "--sat-solver", getattr(args, "sat_solver", "cadical153"), "--implied", str(int(getattr(args, "implied", 0) or 0))] + (["--lazy", "1"] if getattr(args, "lazy", 0) else [])
    t0 = time.time()
    kw = {"start_new_session": True} if os.name != "nt" else {}
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kw)
    ACTIVE.add(p); STARTED[p] = time.time(); RUNNING[p] = (a, b, k, n, time.time())
    try:
        out, err = p.communicate(timeout=limit)
        if p in MEMKILLED:
            MEMKILLED.discard(p); return "MEMKILL", time.time() - t0
        st = out.strip().split()[-1] if out.strip() else "ERROR"
        return (st if st in ("SAT", "UNSAT") else "ERROR"), time.time() - t0
    except subprocess.TimeoutExpired:
        kill_tree(p)
        try: p.communicate(timeout=5)
        except Exception: pass
        return "TIMEOUT", time.time() - t0
    finally:
        ACTIVE.discard(p); STARTED.pop(p, None); RUNNING.pop(p, None)


def dangerous_triple(a, b):
    """True if y = ab + r (a does not divide y), s = b(b+1)+1+k (a does not divide s), x = y + b s = 0 (mod a), x <= n exist
    (n = b^3+2b^2-j^2(j+2)-1): the solution that breaks the template colouring (first b: j=3: 43, j=4: 47, j=5: 57)."""
    j = b - a
    if j < 2: return False
    n = b ** 3 + 2 * b * b - j * j * (j + 2) - 1
    for k in range(0, j + 3):
        s = b * (b + 1) + 1 + k
        if s % a == 0: continue
        for y in range(a * b, a * b + (j + 2) * b):
            if y % a == 0: continue
            x = y + b * s
            if x > n: break
            if x % a == 0 and a * s <= n: return True
    return False


def predict(a, b, k):
    """value predicted by the known formulas / our candidate patterns (used only to choose WHICH n to test first;
    the value is still decided by two SAT calls: n=P-1 colourable and n=P not colourable)"""
    if math.gcd(a, b) != 1: return None
    if k == 2:
        if a == 1: return b * b + 3 * b + 1
        if a > b: return a * a
        if a >= 2 and a <= b: return b * b + b + 1
    if k == 4:
        if (a, b) in PAPER4: return PAPER4[(a, b)]          # values listed in Table 10 of arXiv:2210.03262
        if (a, b) == (2, 3): return 226                      # this project (DRAT-checked)
        if a == b + 1 and a >= 3: return a ** 4 + a ** 3 - 2 * a + 1   # CONJECTURE H3 (FORMULAS.md): (3,2)=103 (paper), (4,3)=313 (ours) fit; (5,4) predicted 741
        if a >= b + 2: return a ** 4                         # CONJECTURE (3 colours: theorem; 4 colours: (3,1)=81,(4,1)=256,(5,1)=625 match; lower bound a^k is Lemma 4.1) - tested by 2 SAT calls
    if a == 1 and b >= 2 and k >= 4:
        m = b + 2; return ((m - 2) * m ** k + 1) // (m - 1)  # pattern; k=4,m<=6 are the paper's values, others are predictions
    if k == 3:
        if a >= b + 2: return a ** 3
        if a == b + 1 and a >= 3: return a ** 3 + (a - 1) ** 2
        if a == 1: m = b + 2; return m ** 3 - m ** 2 - m - 1
        # (j=4 guesses removed 2026-10-26: 3b-108 refuted at (23,27), constant -46 refuted at (27,31); j=4 offsets are irregular)
        # (j=4 guesses removed 2026-10-26: 3b-108 refuted at (23,27), constant -46 refuted at (27,31); j=4 offsets are irregular)
        if b >= 11 and 2 <= b - a and a > int(0.618 * b + 0.73):
            jj = b - a; P = b ** 3 + 2 * b * b - jj ** 2 * (jj + 2)
            return P - a if dangerous_triple(a, b) else P     # corrected conjecture C (2026-10-28): one step (a) lower once the "dangerous triple" exists (j=3: b>=43)   # conjecture C (2026-10-27): R >= b^3+2b^2-j^2(j+2) (j=b-a) in all cells outside formula 1; equality for b large (j=2: b>=17, j=3: b>=23, j=4: b=33). Probes P-1 (expected SAT) and P
        if b >= 11 and 2 <= a <= int(0.618 * b + 0.73): return b ** 3 + b ** 2 + (2 * a + 1) * b + 1   # formula 1 holds up to a line a <= s*b+t (s in [0.600,0.627]; 2026-10-26 analysis: 149/149 cells, b>=11)
        if 7 <= b <= 10 and 2 <= a <= (b + 3) // 2: return b ** 3 + b ** 2 + (2 * a + 1) * b + 1
        if a == b - 1 and b >= 8: return b ** 3 + 2 * b * b + b - 4
    return None


def work(args, path, a, b, k, limit, hard=False, cube_workers=1):
    """advance one (a,b,k) as far as possible within this pass. returns True if exact value known.
    When fewer cells than workers are left, a cell runs SEVERAL probes at once (idle cores are used):
    prediction P-1 and P together, a doubling gallop n, 2n, 4n.., or a (m+1)-ary search instead of bisection."""
    with ACTIVE_LOCK:
        ACTIVE_CELLS[0] += 1
    try:
        return _work(args, path, a, b, k, limit, hard, cube_workers)
    finally:
        with ACTIVE_LOCK:
            ACTIVE_CELLS[0] -= 1


def _work(args, path, a, b, k, limit, hard, cube_workers):
    while not STOP.is_set():
        rows = args._rows_cache(path)
        lo, hi, to = state(rows, a, b, k)
        if hi is not None and hi - lo == 1:
            return True
        m = 1 if (hard or not getattr(args, "multi_probe", 1)) else max(1, min(8, args.workers // max(1, ACTIVE_CELLS[0])))
        pred = predict(a, b, k) if getattr(args, "use_predictions", True) else None
        if hi is None and pred and lo < pred - 1:
            ns = [pred - 1] + ([pred] if m >= 2 else [])      # test the prediction directly: P-1 colourable and P not colourable
        elif hi is None and pred and lo == pred - 1:
            ns = [pred]
        elif hi is None and k == 3 and 2 <= a < b and b >= 7 and lo < b ** 3 + b ** 2 + (2 * a + 1) * b + 1:
            ub = b ** 3 + b ** 2 + (2 * a + 1) * b + 1            # R3 <= formula-1 value in all 165 known cells (a<b, b>=7; 2026-10-26); if SAT there we gallop on
            ns = [ub] + ([max(lo + 1, int(ub * 0.9))] if m >= 2 and int(ub * 0.9) > lo else [])   # deficit was at most 8.2%
        elif hi is None:
            n0 = max(4, lo * 2)
            if lo == 0 and k >= 2 and math.gcd(a, b) == 1 and a ** k - 1 > n0: n0 = a ** k - 1    # R >= a^k (Lemma 4.1)
            ns = [n0]
            while len(ns) < min(m, 2): ns.append(ns[-1] * 2)       # at most 2 gallop probes (a larger n costs memory ~ n^2)
        else:
            ns = mult_probes(a, b, k, lo, hi, m)
            if not ns:
                ns = sorted({lo + (hi - lo) * i // (m + 1) for i in range(1, m + 1)})
                ns = [x for x in ns if lo < x < hi] or [(lo + hi) // 2]
        if not hard:
            ns = [x for x in ns if not (x in to and to[x] >= limit)]       # already tried with this limit
            if not ns:
                return False
        if len(ns) == 1:
            res = [(ns[0],) + tuple(decide(args, a, b, k, ns[0], limit, hard, cube_workers))]
        else:
            out = {}
            def one(x):
                out[x] = decide(args, a, b, k, x, limit, hard, cube_workers)
            ths = [threading.Thread(target=one, args=(x,)) for x in ns]
            for t in ths: t.start()
            for t in ths: t.join()
            res = [(x,) + tuple(out[x]) for x in ns]
        stop_cell = False
        for n, st, sec in res:
            if st == "MEMKILL":
                continue                          # killed by the hard memory cap: nothing written, the loop tries again later
            if st == "INTERRUPTED" or st == "ERROR" or (STOP.is_set() and st == "TIMEOUT"):
                stop_cell = True                  # nothing is written for this probe
                continue
            append(path, {"jst_time": now(), "a": a, "b": b, "k": k, "n": n, "status": st, "seconds": round(sec, 2),
                          "limit_s": ("cube" if hard else limit), "source": ("grid_rado+cubes" if hard else "grid_rado")})
            args._rows_cache.add({"a": str(a), "b": str(b), "k": str(k), "n": str(n), "status": st, "limit_s": str(limit)})
            if st == "TIMEOUT": stop_cell = True
        if stop_cell:
            return False
    return False


ACTIVE_LOCK = threading.Lock()
ACTIVE_CELLS = [0]
SEM = None


class Cache:
    def __init__(self): self.rows = None; self.l = threading.Lock()
    def __call__(self, path):
        with self.l:
            if self.rows is None: self.rows = load(path)
            return list(self.rows)
    def add(self, r):
        with self.l:
            self.rows.append(r)


def keep_awake():
    if os.name == "nt":
        try:
            import ctypes; ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        except Exception: pass


def seed(path):
    """findings of this project (recorded with their JST time and source) so they are never recomputed"""
    if load(path): return
    s = "cube226 (cube-and-conquer, DRAT-checked 14162/14162)"
    append(path, {"jst_time": "2026-10-20 20:10:30", "a": 2, "b": 3, "k": 4, "n": 225, "status": "SAT", "seconds": 12.45, "limit_s": "", "source": "c1_search seed5 (verified colouring)"})
    append(path, {"jst_time": "2026-10-22 02:23:35", "a": 2, "b": 3, "k": 4, "n": 226, "status": "UNSAT", "seconds": "", "limit_s": "", "source": s})


def mem_watchdog(hard_gb):
    """HARD CAP: if the physical memory in use (all of Windows) goes above hard_gb, kill the most recently started
    SAT process (its probe is retried later; nothing is written) and block new starts for 10 minutes."""
    total = None
    try:
        if os.name == "nt":
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                            ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                            ("ae", ctypes.c_ulonglong)]
            m = MS(); m.l = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); total = m.tp / 2 ** 30
        else:
            for line in open("/proc/meminfo"):
                if line.startswith("MemTotal:"): total = int(line.split()[1]) / 2 ** 20
    except Exception:
        total = None
    if not total:
        print(f"[{now()} JST] hard memory cap: total memory unknown -> off", flush=True); return
    print(f"[{now()} JST] hard memory cap: kill the newest SAT run when more than {hard_gb:.0f} of {total:.1f} GB is in use", flush=True)
    while not STOP.is_set():
        time.sleep(5)
        fm = free_mem_gb()
        if fm is None or total - fm <= hard_gb: continue
        procs = sorted(((t, q) for q, t in list(STARTED.items()) if q.poll() is None), key=lambda x: x[0])
        if not procs: continue
        t0, q = procs[-1]
        MEMKILLED.add(q); PRESSURE_UNTIL[0] = time.time() + 600
        print(f"[{now()} JST] hard memory cap: {total - fm:.1f} GB in use > {hard_gb:.0f} GB -> killed the newest SAT run (started {(time.time()-t0)/60:.0f} min ago); it is retried later", flush=True)
        kill_tree(q)
        time.sleep(30)


def run(args):
    out = args.outdir; os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "decisions.csv")
    lock = os.path.join(out, "run.lock")
    if os.path.exists(lock):
        print(f"[stop] lock exists: {lock} (delete it if no run is active)"); sys.exit(2)
    open(lock, "w").write(str(os.getpid()))
    keep_awake(); seed(path)
    args._rows_cache = Cache()
    global SEM
    SEM = threading.Semaphore(args.workers)
    MEM_BUDGET[0] = float(getattr(args, "mem_gb", 0) or 0)
    if getattr(args, "mem_hard_gb", 0):
        threading.Thread(target=mem_watchdog, args=(float(args.mem_hard_gb),), daemon=True).start()
    print(f"[{now()} JST] memory gate: budget {MEM_BUDGET[0]:.0f} GB for the SAT processes (0 = off), free now {free_mem_gb()}", flush=True)
    try:
        tuples = [(a, b, k) for k in range(1, args.K + 1) for s in range(2, 2 * args.N + 1)
                  for a in range(1, args.N + 1) for b in range(1, args.N + 1)
                  if a + b == s and math.gcd(a, b) == 1 and (k <= 3 or max(a, b) <= args.N4)
                  and (not args.ks or k in [int(x) for x in args.ks.split(",")]) and max(a, b) >= args.min_b]
        if args.K >= 4 and args.predict5 and not args.ks: tuples.append((1, 2, 5))   # lowest priority: tests the pattern R_5 = 4*171-1 = 683
        if args.only:      # priority list "a,b,k;a,b,k;...": only these cells are run, in this order (the others just wait, nothing is lost)
            want = [tuple(int(x) for x in t.split(",")) for t in args.only.replace(" ", ";").split(";") if t]
            have = set(tuples) | {(1, 2, 5)}
            tuples = [t for t in want if t in have]
            print(f"[{now()} JST] --only: running {len(tuples)} cells in this order: {tuples}", flush=True)
        p = 0
        while not STOP.is_set():
            limit = args.limit * (4 ** p)
            open_t = [t for t in tuples if not (lambda st: st[1] is not None and st[1] - st[0] == 1)(state(args._rows_cache(path), *t))]
            print(f"[{now()} JST] pass {p}: limit {limit:.0f}s per SAT call; unfinished {len(open_t)}/{len(tuples)}", flush=True)
            if not open_t or p > args.max_pass: break
            hard = p >= args.hard_pass
            ncell = min(len(open_t), args.parallel_cells) if args.parallel_cells > 0 else len(open_t)   # 0 = all open cells at once
            nthr = min(args.workers, ncell) if hard else args.workers
            cw = max(1, -(-args.workers // max(1, ncell))) if hard else 1     # round UP: cells that finish early free cores for the others     # round UP: cells that finish early free cores for the others
            if hard: print(f"[{now()} JST] pass {p} runs as CUBE mode (resumable per cube): {nthr} cells at once, {cw} workers each", flush=True)
            with ThreadPoolExecutor(max_workers=nthr) as ex:
                futs = [ex.submit(work, args, path, a, b, k, limit, hard, cw) for (a, b, k) in open_t]
                t_pass = time.time(); last_pr = 0.0
                while not all(f.done() for f in futs) and not STOP.is_set():
                    time.sleep(2)
                    if time.time() - last_pr > args.progress_minutes * 60:
                        last_pr = time.time()
                        nd = sum(1 for f in futs if f.done())
                        line = f"[{now()} JST] pass {p}: {nd}/{len(futs)} cells finished this pass ({100 * nd // max(1, len(futs))}%), elapsed {(time.time() - t_pass) / 3600:.1f} h"
                        cells_now = set(open_t)
                        cp = [f"{nm}: {u}/{t} cubes ({100 * u // max(t, 1)}%)" for nm, u, t in cube_progress(args, cells_now)] if hard else []
                        rows = args._rows_cache(path)
                        for (ca, cb, ck) in open_t:
                            lo_, hi_, _to = state(rows, ca, cb, ck)
                            if hi_ is not None and hi_ - lo_ == 1: continue
                            runs = [f"n={rn} {(time.time() - rt) / 3600:.2f} h" for q_, (ra, rb, rk, rn, rt) in list(RUNNING.items()) if (ra, rb, rk) == (ca, cb, ck)]
                            cp.append(f"({ca},{cb}) k={ck}: colourable up to {lo_}, not colourable from {hi_ if hi_ is not None else '?'}; running: {', '.join(runs) if runs else '-'}")
                        if cp: line += "\n" + "\n".join("    " + c for c in cp) + "\n"
                        print(line, flush=True)
                        with open(os.path.join(out, "progress.txt"), "a", encoding="utf-8") as pf:
                            pf.write(line + "\n"); pf.flush(); os.fsync(pf.fileno())
                for f in futs: f.result()
            p += 1
        print(f"[{now()} JST] finished. See: python tools\\grid_rado.py report")
    except KeyboardInterrupt:
        STOP.set()
        for q in list(ACTIVE): kill_tree(q)
        print("\n[interrupted] decisions already written are kept; run again to resume")
    finally:
        try: os.remove(lock)
        except OSError: pass


# ---------- report ----------
PAPER4 = {(1, 1): 45, (2, 1): 56, (3, 1): 81, (4, 1): 256, (5, 1): 625, (1, 2): 171, (3, 2): 103, (1, 3): 469, (1, 4): 1037}


def formula_checks(val):
    out = []
    for (a, b, k), v in sorted(val.items()):
        fs = []
        if k == 3 and a >= b + 2 and math.gcd(a, b) == 1: fs.append(("a^3 (Thm 1.2(3), arXiv:2210.03262)", a ** 3))
        if k == 3 and b == a - 1 and a >= 3: fs.append(("a^3+(a-1)^2 (Thm 1.2(2), arXiv:2210.03262)", a ** 3 + (a - 1) ** 2))
        if a == 1 and (b >= 2 or k <= 3):
            m = b + 2
            fs.append((f"((m-2)m^k+1)/(m-1), m={m}  [k=3,4: paper; general k: lower-bound shape of Beutelspacher-Brestovansky; equality for k>=5 not proved]", ((m - 2) * m ** k + 1) // (m - 1)))
        if k == 2 and a == 1: fs.append(("b^2+3b+1 (Thm 3.1, arXiv:1206.4885)", b * b + 3 * b + 1))
        if k == 2 and a > b: fs.append(("a^2 (Thm 3.2, arXiv:1206.4885)", a * a))
        if k == 2 and 2 <= a <= b: fs.append(("b^2+b+1 (Conjecture 3.4, arXiv:1206.4885: conjectured equality)", b * b + b + 1))
        if k == 3 and 2 <= a <= (b + 3) // 2 and b >= 7: fs.append(("b^3+b^2+(2a+1)b+1  [OUR CANDIDATE PATTERN, 2<=a<=(b+3)/2, b>=7; literature not checked]", b ** 3 + b ** 2 + (2 * a + 1) * b + 1))
        if k == 3 and a == b - 1 and b >= 8: fs.append(("b^3+2b^2+b-4  [OUR CANDIDATE PATTERN, a=b-1, b>=8; literature not checked]", b ** 3 + 2 * b * b + b - 4))
        if k == 3 and a == b - 2 and b % 2 == 1 and b >= 11: fs.append(("b^3+2b^2+2b-20  [CANDIDATE 3: a=b-2, b odd >=11; fitted on 3 points b=11,13,15 -> weak]", b ** 3 + 2 * b * b + 2 * b - 20))
        if k == 4 and (a, b) in PAPER4: fs.append(("paper Table 10", PAPER4[(a, b)]))
        for name, fv in fs:
            out.append((a, b, k, v, name, fv, "OK" if v == fv else "MISMATCH"))
    return out


def report(args):
    path = os.path.join(args.outdir, "decisions.csv")
    rows = load(path)
    ks = sorted(set(int(r["k"]) for r in rows)); N = args.N
    val, bnd = {}, {}
    for r in rows:
        a, b, k = int(r["a"]), int(r["b"]), int(r["k"])
        lo, hi, _ = state(rows, a, b, k)
        bnd[(a, b, k)] = (lo, hi)
        if hi is not None and hi - lo == 1: val[(a, b, k)] = hi
    L = [f"# ラド数 R_k(a(x−y)=bz) の表(自動生成)", "", f"- 生成(JST): {now()}", f"- 元データ: `{path}`(SATの判定を1行ずつ追記したログ)",
         "- 値は「R=最小の n で、どの k 色塗りにも単色解がある」。区間は [塗り方が見つかった最大の n+1 以上, 充足不能が確認された最小の n 以下]。gcd(a,b)≠1 は約分した方程式と同じなので「-」。", ""]
    for k in ks:
        L += [f"## {k}色", "", "| b＼a | " + " | ".join(str(a) for a in range(1, N + 1)) + " |", "|---|" + "---|" * N]
        for b in range(1, N + 1):
            cells = []
            for a in range(1, N + 1):
                if math.gcd(a, b) != 1: cells.append("-"); continue
                if (a, b, k) in val: cells.append(str(val[(a, b, k)]))
                elif (a, b, k) in bnd:
                    lo, hi = bnd[(a, b, k)]; cells.append(f"[{lo + 1},{hi if hi else '?'}]")
                else: cells.append("")
            L.append(f"| {b} | " + " | ".join(cells) + " |")
        L.append("")
    L += ["## 既知の式・論文の表との照合", "", "| a | b | k | 計算値 | 式 | 式の値 | 判定 |", "|---|---|---|---|---|---|---|"]
    for t in formula_checks(val): L.append("| " + " | ".join(map(str, t)) + " |")
    L += ["", "## b>a の領域(公式が見つかっていない部分)の値", "", "| (a,b) | " + " | ".join(f"k={k}" for k in ks) + " |", "|---|" + "---|" * len(ks)]
    for a in range(1, N + 1):
        for b in range(a + 1, N + 1):
            if math.gcd(a, b) == 1:
                L.append(f"| ({a},{b}) | " + " | ".join(str(val.get((a, b, k), "")) for k in ks) + " |")
    L += ["", "## この計画で既にわかっていること", "",
          "- R_4(2(x−y)=3z)=226: n=225 は塗り方あり(2026-10-20 20:10:30 JST)、n=226 は14,162個の部分問題が全部充足不能で、DRAT 証明が全件 drat-trim を通過(2026-10-22 02:23:35 JST)。先行研究(2022年の論文では「>225」)での最終確認は未了。",
          "- 2色・3色の表は、論文の定理(Theorem 1.2)と一致する(上の照合表)。",
          "- 色の数 k の向きの規則性(a=1, x−y=(m−2)z, m≥4): R_k = m·R_(k−1) − 1、つまり R_k = ((m−2)·m^k+1)/(m−1) = m^k − m^(k−1) − … − 1。m=4,5,6、k=1〜4 で成り立つ(上の照合表)。m=3(Schur 数)は k=4 で外れる(45≠41)。この形は、一般化されたシュア数の下界として知られているもの(Beutelspacher–Brestovansky の漸化式 R_r ≥ m·R_(r−1) − 1)と同じ形。k≥5 での等号は論文にも証明がない。予想: R_5(x−y=2z)=683(`--predict5` で検証する)。",
          "- 2色: R_2(x−y=bz)=b²+3b+1(定理)、R_2=a²(a>b、定理)、2≤a≤b なら b²+b+1 と予想(arXiv:1206.4885 の Conjecture 3.4)。計算値は全て予想と一致した(例: (2,3)=13、(3,4)=21、(4,5)=31)。",
          "- 3つの数 13, 61, 226(a=2,b=3 の 2色・3色・4色)に当てはまる式は、見つけていない。"]
    op = os.path.join(args.outdir, "TABLES.md")
    with open(op, "w", encoding="utf-8") as f: f.write("\n".join(L) + "\n")
    print("wrote", op)


def decide_cmd(args):
    sys.path.insert(0, HERE)
    from rado_c1 import build_cnf, run_backend, solve_stream_pysat, solve_lazy_pysat
    if args.backend == "pysat" and getattr(args, "lazy", 0):   # only the needed solution clauses (about 1/3 of the memory)
        print(solve_lazy_pysat(args.a, args.b, args.k, args.n, solver=getattr(args, "sat_solver", "cadical153"),
                               log=lambda m: print(m, file=sys.stderr, flush=True))[0])
        return
    if args.backend == "pysat":      # streaming: no solution-set / clause list in memory (big n), same clauses as build_cnf
        print(solve_stream_pysat(args.a, args.b, args.k, args.n, implied=int(getattr(args, "implied", 0) or 0), solver=getattr(args, "sat_solver", "cadical153")))
        return
    cl, nv, _ = build_cnf(args.a, args.b, args.k, args.n)
    st, _m = run_backend(cl, nv, args.backend, args.bin, None)
    print(st)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nme in ("run", "report", "decide"):
        p = sub.add_parser(nme)
        p.add_argument("--outdir", default=os.path.join("results", "rado_grid"))
        p.add_argument("--N", type=int, default=12)
        p.add_argument("--K", type=int, default=4)
        p.add_argument("--N4", type=int, default=5, help="4+ colours only for max(a,b)<=N4 (they are very hard beyond that)")
        p.add_argument("--workers", type=int, default=11)
        p.add_argument("--backend", choices=["pysat", "cadical"], default="pysat")
        p.add_argument("--bin", default="cadical")
        p.add_argument("--limit", type=float, default=600, help="seconds per SAT call in pass 0 (x4 each pass)")
        p.add_argument("--max-pass", type=int, default=6)
        p.add_argument("--cube-root", default=None, help="working folder of the cube searches (default: <outdir>\\cubes); e.g. D:\\sat_work\\cubes on an SSD")
        p.add_argument("--hard-pass", type=int, default=3, help="from this pass on, long calls run as resumable cube searches")
        p.add_argument("--cube-depth", type=int, default=10)
        p.add_argument("--progress-minutes", type=float, default=10)
        p.add_argument("--min-b", type=int, default=0, help="focus mode: only cells with max(a,b)>=this")
        p.add_argument("--implied", type=int, default=0, help="1 = cube mode adds implied clauses (scaling lemma); see rado_c1.implied_clauses")
        p.add_argument("--sat-solver", default="cadical153", help="pysat solver for single SAT calls: cadical153 (old default) or minisat22 (2026-10-28: ~20x faster, ~1/3 memory on 3-colour instances)")
        p.add_argument("--lazy", type=int, default=0, help="1 = lazy solving: start with 2%% of the solution clauses and add only the violated ones (memory about 1/3; results are exact)")
        p.add_argument("--mem-hard-gb", type=float, default=26, help="HARD CAP on the memory in use by the whole PC (GB): above it the newest SAT run is killed and retried later. 0 = off")
        p.add_argument("--mem-gb", type=float, default=20, help="memory budget (GB) for the running SAT processes (estimate ~150 bytes per clause); a probe waits until it fits. 0 = off")
        p.add_argument("--multi-probe", type=int, default=1, help="1 = when fewer cells than workers are open, a cell runs several probes at once (uses idle cores); 0 = one probe per cell")
        p.add_argument("--parallel-cells", type=int, default=0, help="cube mode: how many cells run at once (0 = all open cells). 1 = one cell at a time with ALL workers, next cell starts when it finishes (priority order of --only)")
        p.add_argument("--only", default="", help='priority list of cells "a,b,k;a,b,k": only these are run (e.g. "1,4,4;5,1,4")')
        p.add_argument("--ks", default="", help="focus mode: comma list of colour counts, e.g. 3")
        p.add_argument("--predict5", type=int, default=1, help="also test the prediction R_5(x-y=2z)=683 (last in the queue)")
        if nme == "decide":
            p.add_argument("--a", type=int); p.add_argument("--b", type=int); p.add_argument("--k", type=int); p.add_argument("--n", type=int)
    a = ap.parse_args()
    {"run": run, "report": report, "decide": decide_cmd}[a.cmd](a)


if __name__ == "__main__":
    main()

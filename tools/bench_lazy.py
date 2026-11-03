# -*- coding: utf-8 -*-
r"""Compare the LAZY solver (rado_c1.solve_lazy_pysat, keeps only the needed clauses) with the normal full CNF on
cells whose value is already known.  One row per run in results\bench_lazy.csv (JST time, seconds, peak memory);
finished runs are skipped on restart (Ctrl+C is safe).  Run:  python tools\bench_lazy.py"""
import csv, os, sys, time, subprocess
from datetime import datetime, timezone, timedelta
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
JST = timezone(timedelta(hours=9))
OUT = os.path.join(HERE, "..", "results", "bench_lazy.csv")
CASES = [(22, 35, 3, 45675, "SAT"), (22, 35, 3, 45676, "UNSAT")]   # R3(22(x-y)=35z) = 45676 (known)


def peak_gb():
    try:
        import ctypes, ctypes.wintypes as w
        class PMC(ctypes.Structure):
            _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("a", ctypes.c_size_t), ("b", ctypes.c_size_t), ("c", ctypes.c_size_t),
                        ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        p = PMC(); p.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(p), p.cb)
        return round(p.PeakWorkingSetSize / 2 ** 30, 2)
    except Exception:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 20, 2)


def one(mode, a, b, k, n):
    """runs in a child process so that the peak memory belongs to this run only"""
    from rado_c1 import solve_lazy_pysat, solve_stream_pysat
    t = time.time()
    if mode == "lazy":
        st, info = solve_lazy_pysat(a, b, k, n, log=lambda m: print("   ", m, flush=True))
        extra = f"rounds={info['rounds']} clauses={info['added']}"
    else:
        st = solve_stream_pysat(a, b, k, n); extra = ""
    print(f"RESULT {st} {time.time() - t:.1f} {peak_gb()} {extra}", flush=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "one":
        one(sys.argv[2], *map(int, sys.argv[3:7])); return
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            done.add((r["mode"], r["a"], r["b"], r["n"]))
    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["jst_time", "mode", "a", "b", "k", "n", "status", "expected", "seconds", "peak_gb", "note"]); f.flush()
        for mode in ("lazy",):          # full runs are known: 45675 SAT 28 min, 45676 UNSAT 18 min (decisions.csv, 2026-10-26), about 8-10 GB
            for a, b, k, n, exp in CASES:
                if (mode, str(a), str(b), str(n)) in done: continue
                print(f"[{datetime.now(JST):%Y-%m-%d %H:%M:%S} JST] {mode} ({a},{b}) k={k} n={n} ...", flush=True)
                p = subprocess.run([sys.executable, __file__, "one", mode, str(a), str(b), str(k), str(n)], capture_output=True, text=True)
                line = [l for l in p.stdout.splitlines() if l.startswith("RESULT")]
                if not line:
                    print("   failed:", p.stderr[-300:]); continue
                _, st, sec, pk, *ex = line[0].split()
                print(f"   -> {st} (expected {exp}) {float(sec)/60:.1f} min, peak {pk} GB {' '.join(ex)}", flush=True)
                w.writerow([f"{datetime.now(JST):%Y-%m-%d %H:%M:%S}", mode, a, b, k, n, st, exp, sec, pk, " ".join(ex)]); f.flush(); os.fsync(f.fileno())


if __name__ == "__main__":
    main()

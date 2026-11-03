# -*- coding: utf-8 -*-
r"""Tuning benchmark for cube_search.py with --implied 1 on a known UNSAT cell ((5,2), n=625, 4 colours).
Each variant runs for at most --cap seconds with --workers workers (fresh folder), then it is killed and the number of
finished cubes is read with cube_search.py --report.  If a variant finishes (UNSAT) the time is recorded.
Results are appended to results\bench_tune.csv (JST).  Resumable: variants already in the CSV are skipped.
Usage: python tools\bench_tune.py --workers 4 --cap 1200
"""
import argparse, csv, os, re, shutil, subprocess, sys, time
from datetime import datetime, timezone, timedelta
HERE = os.path.dirname(os.path.abspath(__file__))
JST = timezone(timedelta(hours=9))
def now(): return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
def kill_tree(p):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            p.kill()
    except Exception:
        pass
VARIANTS = [("base", {}), ("noimplied", {"--implied": "0"}), ("implied2", {"--implied": "2"}), ("budget5000", {"--budget": "5000"}),
            ("budget100000", {"--budget": "100000"}), ("depth8", {"--depth": "8"}), ("depth12", {"--depth": "12"}),
            ("split2", {"--split": "2"}), ("split4", {"--split": "4"})]
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--cap", type=float, default=1200)
    ap.add_argument("--root", default=r"D:\sat_work\bench_tune")
    ap.add_argument("--a", default="5"); ap.add_argument("--b", default="2"); ap.add_argument("--n", default="625")
    args = ap.parse_args()
    csvp = os.path.join(HERE, "..", "results", "bench_tune.csv"); os.makedirs(os.path.dirname(csvp), exist_ok=True)
    done = set()
    if os.path.exists(csvp):
        done = {r["variant"] for r in csv.DictReader(open(csvp, encoding="utf-8"))}
    for name, ov in VARIANTS:
        if name in done: continue
        out = os.path.join(args.root, name); shutil.rmtree(out, ignore_errors=True); os.makedirs(out, exist_ok=True)
        opts = {"--a": args.a, "--b": args.b, "--k": "4", "--n": args.n, "--depth": "10", "--workers": str(args.workers),
                "--backend": "pysat", "--budget": "20000", "--split": "3", "--implied": "1", "--log-minutes": "30", "--outdir": out}
        opts.update(ov)
        cmd = [sys.executable, os.path.join(HERE, "cube_search.py")] + [x for kv in opts.items() for x in kv]
        print(f"[{now()} JST] variant {name} {ov}", flush=True)
        t0 = time.time(); p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while time.time() - t0 < args.cap and p.poll() is None: time.sleep(5)
        fin = p.poll() is not None
        if not fin: kill_tree(p); p.wait()
        secs = time.time() - t0
        rep = subprocess.run([sys.executable, os.path.join(HERE, "cube_search.py"), "--report"] + [x for kv in opts.items() for x in kv],
                             capture_output=True, text=True).stdout
        m = re.search(r"cubes=(\d+) UNSAT=(\d+) SAT=(\d+)", rep)
        tot, uns, sat = (int(m.group(i)) for i in (1, 2, 3)) if m else (0, 0, 0)
        new = not os.path.exists(csvp)
        with open(csvp, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new: w.writerow(["jst_time", "variant", "workers", "cap_s", "finished", "seconds", "cubes_total", "cubes_unsat", "fraction", "sat"])
            w.writerow([now(), name, args.workers, args.cap, int(fin), round(secs, 1), tot, uns, round(uns / tot, 4) if tot else "", sat]); f.flush(); os.fsync(f.fileno())
        print(f"[{now()} JST] {name}: finished={fin} {secs:.0f}s cubes {uns}/{tot} ({(uns/tot if tot else 0):.1%}) SAT={sat}", flush=True)
if __name__ == "__main__":
    main()

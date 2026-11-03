# -*- coding: utf-8 -*-
r"""Run many cells in parallel (one process per cell), up to --workers at a time (i5-11400F: 11), memory-safe:
  * every cell has a memory ESTIMATE; the sum of the estimates of the running cells must stay below a BUDGET
    (= free memory when this script starts - --keep-free GB), so processes that are still growing are counted too
    (the old version looked only at the current free memory and started too many at once),
  * a new cell also needs (free memory now) - (its estimate) >= --keep-free,
  * if free memory still falls below --kill-below GB, the newest cell is killed, put back at the END of the queue,
    and the number of workers is lowered by one for the rest of the run (so it does not happen again and again).
Estimates (GB): subset S(n) ~ 3*(n/b)^2/2 ternary clauses at ~55 bytes (MiniSat) -> 8.5e-8*(n/b)^2 + 0.6;
exact_big adds the numpy template check (~40 bytes per number).
Tools: (default) exact_big.py cells j,b / f1,a,b ; --tool subset: subset_check.py --cells a,b,n ; --tool smin: s_min.py cells j,b.
Ctrl+C is safe (running cells are lost, finished rows stay).  Run: python tools\run_parallel.py --workers 11 --tool smin 5,81 ..."""
import os, subprocess, sys, time
from datetime import datetime, timezone, timedelta
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from grid_rado import free_mem_gb
JST = timezone(timedelta(hours=9))
TOOL = ["exact_big.py"]


def est(cell):
    p = [int(t) for t in cell.split(",") if t.lstrip("-").isdigit()]
    if TOOL[0] == "collect_colorings.py":            # full CNF of [1,n] with MiniSat: ~ 1.5 n^2/b clauses
        a, b, n = p[0], p[1], p[2]
        return 5.0e-8 * n * n / b + 0.5
    if TOOL[0] == "subset_check.py":
        a, b, n = p[0], p[1], p[2]
    else:                                        # j,b  or  f1,a,b
        b = p[-1]; n = b ** 3 + 2 * b * b
    g = 5.0e-8 * (n / b) ** 2 + 0.5           # MiniSat ternary clause ~36 bytes (re-measured from 66: 4-5 cells of b~80 used ~14 GB)
    if TOOL[0] == "exact_big.py": g += 40 * n / 2 ** 30
    return g


def main():
    args = sys.argv[1:]; W, keep, killb = 11, 4.0, 2.5
    while args and args[0].startswith("--"):
        k, v = args[0], args[1]; args = args[2:]
        if k == "--workers": W = int(v)
        elif k == "--keep-free": keep = float(v)
        elif k == "--kill-below": killb = float(v)
        elif k == "--tool": TOOL[0] = {"subset": "subset_check.py", "smin": "s_min.py", "collect": "collect_colorings.py"}.get(v, "exact_big.py")
    queue = list(args); running = {}
    total_w = sum(est(c) for c in queue); done_w = [0.0]; t_start = time.time(); ndone = [0]; ntotal = len(queue)
    now = lambda: datetime.now(JST).strftime("%H:%M:%S")
    fm0 = free_mem_gb(); budget = (fm0 - keep) if fm0 is not None else 20.0
    print(f"[{now()}] free {fm0 if fm0 is None else round(fm0, 1)} GB -> budget for the cells {budget:.1f} GB, workers {W}", flush=True)
    try:
        while queue or running:
            for c, (p, t0, e) in list(running.items()):
                if p.poll() is not None:
                    del running[c]; ndone[0] += 1; done_w[0] += est(c)
                    el = time.time() - t_start; eta = el / max(done_w[0], 1e-9) * (total_w - done_w[0])
                    print(f"[{now()}] finished {c} ({time.time() - t0:.0f}s)   done {ndone[0]}/{ntotal}, elapsed {el/60:.0f} min, "
                          f"ETA about {eta/60:.0f} min (rough: by memory estimate)", flush=True)
            fm = free_mem_gb()
            if fm is not None and fm < killb and running:
                c = max(running, key=lambda k: running[k][1]); running[c][0].kill(); del running[c]; queue.append(c)
                W = max(1, min(W, len(running) + 1) - 1)
                print(f"[{now()}] free memory {fm:.1f} GB < {killb} -> killed {c} (moved to the end of the queue), workers now {W}", flush=True)
                time.sleep(30); continue
            used = sum(e for _, _, e in running.values())
            started = False
            for i, c in enumerate(queue):                     # first cell in the queue that fits
                e = est(c)
                if len(running) >= W: break
                if used + e <= budget and (fm is None or fm - e >= keep):
                    queue.pop(i)
                    cmd = [sys.executable, os.path.join(HERE, TOOL[0])] + (["--cells"] if TOOL[0] == "subset_check.py" else []) + [c]
                    running[c] = (subprocess.Popen(cmd), time.time(), e); started = True
                    print(f"[{now()}] start {c} (est {e:.1f} GB, reserved {used + e:.1f}/{budget:.1f} GB, running {len(running)})", flush=True)
                    break
            if not running and queue and not started:
                c = queue.pop(0); e = est(c)                 # bigger than the budget: run it alone
                cmd = [sys.executable, os.path.join(HERE, TOOL[0])] + (["--cells"] if TOOL[0] == "subset_check.py" else []) + [c]
                running[c] = (subprocess.Popen(cmd), time.time(), e); started = True
                print(f"[{now()}] start {c} ALONE (est {e:.1f} GB > budget)", flush=True)
            time.sleep(3 if started else 5)
    except KeyboardInterrupt:
        for p, _, _ in running.values(): p.kill()
        print("Ctrl+C: stopped (finished rows are kept)")


if __name__ == "__main__":
    main()

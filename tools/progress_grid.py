# -*- coding: utf-8 -*-
r"""
Progress of a running grid_rado.py (works with the OLD and the NEW version; read-only).
  python tools\progress_grid.py --pass-start "2026-10-22 10:39:52" --limit 9600
--pass-start / --limit : copy them from the last 'pass N: limit ...s' line on the screen (time and seconds).
For every unfinished cell it prints: known range [lo, hi], what it is doing, and the latest time its current call can run to.
"""
import argparse, csv, math, os, sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
JST = timezone(timedelta(hours=9))
from grid_rado import load, state

ap = argparse.ArgumentParser()
ap.add_argument("--outdir", default=os.path.join("results", "rado_grid"))
ap.add_argument("--pass-start", required=True)
ap.add_argument("--limit", type=float, required=True)
ap.add_argument("--N", type=int, default=16); ap.add_argument("--N4", type=int, default=5)
a = ap.parse_args()
rows = load(os.path.join(a.outdir, "decisions.csv"))
t_pass = datetime.strptime(a.pass_start, "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
now = datetime.now(JST)
cells = {}
for r in rows:
    key = (int(r["a"]), int(r["b"]), int(r["k"]))
    cells.setdefault(key, []).append(r)
open_cells, finished_this_pass, latest_end = [], 0, t_pass
for key, rs in sorted(cells.items(), key=lambda kv: (kv[0][2], kv[0][0] + kv[0][1])):
    k = key[2]
    if k == 4 and max(key[0], key[1]) > a.N4: continue
    lo, hi, to = state(rows, *key)
    if hi is not None and hi - lo == 1: continue
    last = rs[-1]
    lt = datetime.strptime(last["jst_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
    done_this_pass = last["status"] == "TIMEOUT" and float(last["limit_s"] or 0) >= a.limit and lt >= t_pass
    if done_this_pass:
        finished_this_pass += 1
        what = "pass finished for this cell (timed out)"
    else:
        start = max(lt, t_pass)
        end = start + timedelta(seconds=a.limit)
        latest_end = max(latest_end, end)
        el = (now - start).total_seconds()
        what = f"current call since {start:%H:%M} -> at most until {end:%m-%d %H:%M} ({min(100, 100 * el / a.limit):.0f}% of the limit used)"
    open_cells.append((key, lo, hi, what))
for key, lo, hi, what in open_cells:
    print(f"k={key[2]} (a={key[0]},b={key[1]}): R in [{lo + 1}, {hi if hi else '?'}]  {what}")
tot = len(open_cells)
print(f"\n{finished_this_pass}/{tot} cells finished this pass ({100 * finished_this_pass // max(tot, 1)}%).")
print(f"This pass can last at most until {latest_end:%Y-%m-%d %H:%M} JST (worst case: every call uses its full limit; a cell that finishes a call early starts its next call, so a cell can also run a little longer).")
print(f"Next pass limit would be {a.limit * 4:.0f} s = {a.limit * 4 / 3600:.1f} h per call.")

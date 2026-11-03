"""Read-only: speed and estimated finish for every open cube cell (does not touch the running program).
 PowerShell:  python tools\\eta_cubes.py --root D:\\sat_work\\cubes --window-min 30
Counts a cube as finished when it is UNSAT/SAT, or split and all its children are UNSAT (same rule as cube_search.read_state)."""
import argparse, csv, os, re, sys, time
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
JST = timezone(timedelta(hours=9))

def load(d):
    rows = []
    for fn in os.listdir(d):
        if fn.startswith("cubes_w") and fn.endswith(".csv"):
            with open(os.path.join(d, fn), newline="", encoding="utf-8") as f:
                rows += list(csv.DictReader(f))
    for r in rows:
        r["t"] = datetime.strptime(r["jst_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST).timestamp()
    rows.sort(key=lambda r: r["t"])
    return rows

def finished(rows, cutoff):
    done, split, ch = {}, {}, {}
    for r in rows:
        if r["t"] > cutoff: break
        c = int(r["cube"]); note = r.get("note") or ""
        if r["status"] == "SPLIT": split[c] = int(note.split("=")[1])
        elif note.startswith("child:"):
            if r["status"] in ("SAT", "UNSAT"): ch[(c, int(note.split(":")[1]))] = r["status"]
        elif r["status"] in ("SAT", "UNSAT"): done[c] = r["status"]
    for c, n in split.items():
        if c not in done and all(ch.get((c, j)) == "UNSAT" for j in range(n)): done[c] = "UNSAT"
    nchild = sum(1 for k in ch)          # children finished (work done inside split cubes)
    return len(done), len(split), nchild

def fmt(h):
    return "-" if h is None else (f"{h*60:.0f} min" if h < 1 else f"{h:.1f} h" if h < 48 else f"{h/24:.1f} days")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True); ap.add_argument("--window-min", type=float, default=30)
    ap.add_argument("--depth", type=int, default=10)
    a = ap.parse_args()
    from cube_search import enum_cubes
    now = time.time(); w = a.window_min * 60
    print(f"[{datetime.now(JST):%Y-%m-%d %H:%M:%S} JST] speed over the last {a.window_min:.0f} min\n")
    for name in sorted(os.listdir(a.root)):
        m = re.match(r"a(\d+)_b(\d+)_k(\d+)_n(\d+)$", name)
        d = os.path.join(a.root, name)
        if not m or not os.path.isdir(d) or os.path.exists(os.path.join(d, "FINAL.txt")) and "all_unsat=YES" in open(os.path.join(d, "FINAL.txt")).read():
            continue
        tot = len(enum_cubes(int(m[1]), int(m[2]), int(m[3]), a.depth))
        rows = load(d)
        n1, s1, c1 = finished(rows, now); n0, s0, c0 = finished(rows, now - w)
        rate = (n1 - n0) / (a.window_min / 60)            # finished cubes per hour
        eta = (tot - n1) / rate if rate > 0 else None
        print(f"{name}: {n1}/{tot} cubes ({100*n1/tot:.0f}%), +{n1-n0} in {a.window_min:.0f} min, "
              f"split cubes {s1} (children done {c1}), ETA {fmt(eta)}\n")
    print("ETA is a straight-line guess: cubes finish at uneven speed (hard ones are often last).")

if __name__ == "__main__":
    main()

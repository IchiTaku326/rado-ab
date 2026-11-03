# -*- coding: utf-8 -*-
r"""Upper bound (rigorous) and conjectured exact value of R3((b-j)(x-y)=bz) from the small set S only:
   scan n = P0 + k*a (k = 0, 1, 2, 3, ... in order; the first run used a binary search, which is WRONG because S(n) is not monotone in n; P0 = N - j^2(j+2) - t*a from the steps formula, a = b-j) and stop at the first n
   where S(n) = {a | x} U {x = n (mod b)} is not 3-colourable.  Then R <= n (always true).
   Conjecture (true for all 400+ known values): R is a multiple of a and S(R) is not colourable -> R = that n exactly.
   e = (N - j^2(j+2) - R)/a is written too (e = t - k).
Cell: j,b.  One row per cell in results\s_min.csv (skipped if present; Ctrl+C is safe).  Run: python tools\s_min.py 5,43"""
import csv, math, os, sys, time
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subset_check import solve_subset
JST = timezone(timedelta(hours=9))
BASE = os.environ.get("SMIN_BASE", "0") == "1"      # 1: start at base(a,b) of the unified formula (output s_min3.csv)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "s_min3.csv" if BASE else "s_min2.csv")
OLD = {}                                              # cell -> {k: unsat?} from the first run (results\s_min.csv)
_old = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "s_min.csv")
if os.path.exists(_old) and not BASE:
    for _r in csv.DictReader(open(_old, encoding="utf-8")):
        OLD[_r["cell"]] = {int(t.split(":")[0]): t.split(":")[1] == "U" for t in _r["tried"].split()}
KFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "s_min3_k.csv" if BASE else "s_min2_k.csv")   # every single solve (cell,k,U/S): a restart loses nothing
if os.path.exists(KFILE):
    for _l in open(KFILE, encoding="utf-8"):
        _p = _l.strip().split(",")
        if len(_p) == 4: OLD.setdefault(_p[0] + "," + _p[1], {})[int(_p[2])] = _p[3] == "U"


def main():
    for cell in sys.argv[1:]:
        j, b = map(int, cell.split(",")); a = b - j
        if a < 2 or math.gcd(a, b) != 1: print("skip", cell); continue
        done = set()
        if os.path.exists(OUT):
            for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add(r["cell"])
        if cell in done: print("done already:", cell); continue
        N = b ** 3 + 2 * b * b; C = j * j * (j + 2); t = max(0, j - 1 - (-(-j * (j * j + j + 1) // a)))
        P0 = (N - C - t * a) if not BASE else (N - (j - 1) * b + ((-j * (j * j + j + 1)) % a)); t0 = time.time(); tried = []; memo = dict(OLD.get(cell, {}))   # results of the first run are reused
        kmax = min([k for k, u in memo.items() if u] + [200])                              # an UNSAT k from before = upper bound
        def uns(k):                                   # S(P0 + k a) not colourable?
            if k not in memo:
                memo[k] = solve_subset(a, b, P0 + k * a)[0] == "UNSAT"
                with open(KFILE, "a", encoding="utf-8") as kf:
                    kf.write(f"{cell},{k},{'U' if memo[k] else 'S'}\n"); kf.flush(); os.fsync(kf.fileno())
            tried.append(f"{k}:{'U' if memo[k] else 'S'}")
            return memo[k]
        # SEQUENTIAL scan k = 0, 1, 2, ... (S(n) is NOT monotone in n: the residue class changes with n, so no binary search)
        n = None
        for k in range(0, kmax + 1):
            if uns(k): n = P0 + k * a; break
        new = not os.path.exists(OUT)
        with open(OUT, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new: w.writerow(["jst_time", "cell", "j", "a", "b", "t", "P0", "R_upper", "e" if not BASE else "e", "tried", "seconds"])
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), cell, j, a, b, t, P0, n,
                        "" if n is None else (N - C - n) // a, " ".join(tried), round(time.time() - t0, 1)])
            fh.flush(); os.fsync(fh.fileno())
        print(f"{cell}: a={a} t={t}  R <= {n}  (e = {'' if n is None else (N - C - n) // a})  tried {' '.join(tried)}  {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

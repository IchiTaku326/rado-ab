# -*- coding: utf-8 -*-
r"""Structure of the extremal colourings: all valid k-colourings of [1, a^k - 1] (up to colour renaming = first-fit order)
for small cells.  Questions: how many are there?  is the 'a-adic valuation colouring' (Lemma 4.1 of arXiv:2210.03262) the only one?
which pairs (x,y) have the same colour in ALL of them (forced equalities) -> candidate lemmas for the SAT encoding.
Output: results\extremal.txt (append, JST).  Usage: python tools\extremal.py [--cap 20000]
"""
import argparse, os, sys, time
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rado_c1 import build_cnf
JST = timezone(timedelta(hours=9))
def now(): return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
def val(a, x):
    e = 0
    while x % a == 0: x //= a; e += 1
    return e
def canon(col):
    m = {}; out = []
    for c in col:
        if c not in m: m[c] = len(m)
        out.append(m[c])
    return tuple(out)
def runs(col):
    out = []; s = 0
    for i in range(1, len(col) + 1):
        if i == len(col) or col[i] != col[s]:
            out.append(f"{s+1}-{i}:{col[s]}" if i - s > 1 else f"{s+1}:{col[s]}"); s = i
    return " ".join(out)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cap", type=int, default=20000)
    ap.add_argument("--cells", default="3,1,2;5,2,2;5,3,2;7,5,2;3,1,3;4,1,3;5,2,3;5,3,3;7,5,3")
    args = ap.parse_args()
    from pysat.solvers import Glucose4
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "extremal.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    def log(s):
        print(s, flush=True)
        with open(out, "a", encoding="utf-8") as f: f.write(s + "\n"); f.flush(); os.fsync(f.fileno())
    for t in args.cells.split(";"):
        a, b, k = (int(x) for x in t.split(","))
        n = a ** k - 1
        cl, nv, v = build_cnf(a, b, k, n)
        S = Glucose4(bootstrap_with=cl); sols = []; t0 = time.time()
        while len(sols) < args.cap and S.solve():
            m = set(l for l in S.get_model() if l > 0)
            col = [next(c for c in range(k) if v(x, c) in m) for x in range(1, n + 1)]
            sols.append(tuple(col)); S.add_clause([-v(x, col[x - 1]) for x in range(1, n + 1)])
        S.delete()
        done = len(sols) < args.cap
        valc = canon([min(val(a, x), k - 1) for x in range(1, n + 1)])
        has = tuple(valc) in set(sols)
        log(f"[{now()} JST] (a,b,k)=({a},{b},{k}) n={n}: {len(sols)}{'' if done else '+ (cap)'} colourings up to renaming, valuation colouring present={has}, {time.time()-t0:.0f}s")
        if sols:
            # forced equalities: classes of the common refinement
            sig = {}
            for x in range(1, n + 1):
                sig.setdefault(tuple(s[x - 1] for s in sols), []).append(x)
            log(f"    common refinement: {len(sig)} blocks (blocks = numbers that have the same colour in ALL the colourings found)")
            if len(sols) <= 6:
                for s in sols: log("    " + runs(s))
            for key, xs in list(sig.items())[:12]:
                log(f"    block size {len(xs)}: {xs[:12]}{' ...' if len(xs) > 12 else ''}")
if __name__ == "__main__":
    main()

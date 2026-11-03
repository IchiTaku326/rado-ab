# -*- coding: utf-8 -*-
r"""Summary of the check of R3 = N(a,b) = min(a*m', M+ab+1) from results\subset_K_bb1.csv (n = N rows only).
UNSAT = S not colourable at N -> R3 <= N, with the theorem R3 >= N: R3 = N (upper bound by MiniSat, no DRAT).
SAT = S colourable at N: no upper bound from S (the conjecture or the S method fails there -> look at it)."""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from conj_jobs import N
f = os.path.join(HERE, "..", "results", "subset_K_bb1.csv")
cnt = {}; sat = []
for r in csv.DictReader(open(f, encoding="utf-8")):
    a, b, n = int(r["a"]), int(r["b"]), int(r["n"])
    if n != N(a, b): continue
    cnt[r["result"]] = cnt.get(r["result"], 0) + 1
    if r["result"] != "UNSAT": sat.append((a, b, n, r["result"]))
bs = sorted({int(r["b"]) for r in csv.DictReader(open(f, encoding="utf-8"))})
print(f"rows with n = N(a,b): {cnt}   (b up to {bs[-1] if bs else '-'})")
print("not UNSAT:", sat[:40])

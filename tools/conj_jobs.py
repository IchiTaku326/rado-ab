# -*- coding: utf-8 -*-
r"""Jobs for checking the 3-colour conjecture  R3 = N(a,b) = min(a*m', M+ab+1)  (2026-10-31; lower bound R3 >= N is a theorem):
the upper bound needs S = {a*m : m <= b^2+b+1} U {x = N (mod b)} not 3-colourable at n = N (subset_check.py, SUBSET_K=bb1).
Prints  a,b,N  for 2 <= a < b, gcd = 1, BMIN <= b <= BMAX, b from small to large, leaving out cells whose value is already known
(results\s_min3.csv, decisions.csv via known_R) and cells already in results\subset_K_bb1.csv.  Run: python tools\conj_jobs.py 82 90"""
import csv, os, sys
from math import gcd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from subset_check import known_R


def N(a, b):
    M = b * (b * b + b + a + 1)
    A = {a * up + b * u for u in range(1, b + 1) for up in range(1, b + 1)}
    return min([a * m for m in A if a * m > M] + [M + a * b + 1])


if __name__ == "__main__":
    b0, b1 = int(sys.argv[1]), int(sys.argv[2])
    known = set(known_R())
    f = os.path.join(HERE, "..", "results", "s_min3.csv")
    if os.path.exists(f):
        for r in csv.DictReader(open(f, encoding="utf-8-sig")): known.add((int(r["a"]), int(r["b"])))
    f = os.path.join(HERE, "..", "results", "subset_K_bb1.csv")
    if os.path.exists(f):
        for r in csv.DictReader(open(f, encoding="utf-8")): known.add((int(r["a"]), int(r["b"])))
    print(" ".join(f"{a},{b},{N(a, b)}" for b in range(b0, b1 + 1) for a in range(2, b) if gcd(a, b) == 1 and (a, b) not in known))

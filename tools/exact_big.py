# -*- coding: utf-8 -*-
r"""Exact values for BIG b, cheaply (2026-10-29):
   lower bound  R >= P : the template colouring of [1, P-1] has no monochromatic solution (all solutions checked, numpy)
   upper bound  R <= P : the small set S(P) = {a | x} U {x = P (mod b)} is not 3-colourable (MiniSat; see subset_check.py)
   both -> R = P exactly (MiniSat result, no DRAT).
Predictions P (N = b^3+2b^2, a = b-j):
   f1   (formula 1, a^2+(b-1)a <= b^2+b+1): P = b^3+b^2+(2a+1)b+1,  template of the formula-1 theorem
   j=1 : P = N+b-4;  j>=2 : P = N - j^2(j+2) - t*a,  t = max(0, j-1-ceil(j(j^2+j+1)/a))   (the "steps" conjecture)
         template h=j+1, end block 2b, n = P-1   (the j=1,2,3,4 theorems)
Cells: j,b   or   f1,a,b .  Results: results\exact_big.csv (rows already there are skipped; Ctrl+C is safe).
Run: python tools\exact_big.py 4,89 4,91 3,61 f1,40,66"""
import csv, math, os, sys, time
from datetime import datetime, timezone, timedelta
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subset_check import solve_subset
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "exact_big.csv")


def val(x, a):
    v = np.zeros(len(x), dtype=np.int64); t = x.copy(); t[0] = 1
    for _ in range(12):
        m = (t % a == 0); v[m] += 1; t[m] //= a
    return v


def colour_j(a, b, n, h):
    x = np.arange(n + 1, dtype=np.int64); v = val(x, a); c = np.full(n + 1, 2, np.int8)
    c[(v == 0) & ((x <= a * b - 1) | (x >= n - 2 * b))] = 0
    c[(v == 1) & (x // a <= b * (b + 1))] = 1
    q = x // (a * a); c[(v >= 2) & (q <= b)] = 0; c[(v >= 2) & (q > b) & (q <= b + h)] = 1
    return c


def colour_f1(a, b, n):
    x = np.arange(n + 1, dtype=np.int64); a1 = (x % a == 0); a2 = (x % (a * a) == 0); c = np.full(n + 1, 2, np.int8)
    c[a1 & (x <= a * b * (b + 1))] = 1; c[(~a1) & (x <= a * b - 1)] = 0; c[a2 & (x <= b * a * a)] = 0; c[x > n - a * b] = 0
    return c


def mono(a, b, n, c):
    s, tot = 1, 0
    while b * s <= n - 1 and a * s <= n:
        d, z = b * s, a * s; y = np.arange(1, n - d + 1)
        tot += int(((c[y] == c[y + d]) & (c[y] == c[z])).sum()); s += 1
    return tot


def main():
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add(r["cell"])
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "cell", "a", "b", "j", "t", "P", "template_violations", "subset_size", "subset_result", "verdict", "seconds"])
    for cell in sys.argv[1:]:
        if cell in done: print("done already:", cell); continue
        p = cell.split(",")
        if p[0] == "f1":
            a, b = int(p[1]), int(p[2]); j = b - a; t = ""
            P = b ** 3 + b * b + (2 * a + 1) * b + 1
        else:
            j, b = int(p[0]), int(p[1]); a = b - j; N = b ** 3 + 2 * b * b
            if math.gcd(a, b) != 1: print("skip (gcd>1):", cell); continue
            if j == 1: t = -1; P = N + b - 4
            else:
                t = max(0, j - 1 - (-(-j * (j * j + j + 1) // a))); P = N - j * j * (j + 2) - t * a
        t0 = time.time()
        print(f"[{datetime.now(JST):%H:%M:%S}] {cell}: a={a} b={b} P={P} (t={t}) ...", flush=True)
        c = colour_f1(a, b, P - 1) if p[0] == "f1" else colour_j(a, b, P - 1, j + 1)
        bad = mono(a, b, P - 1, c); del c
        res, size, m = solve_subset(a, b, P)
        verdict = ("R = P" if bad == 0 and res == "UNSAT" else
                   ("R <= P (template fails)" if res == "UNSAT" else ("R >= P (subset SAT)" if bad == 0 else "nothing")))
        w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), cell, a, b, j, t, P, bad, size, res, verdict, round(time.time() - t0, 1)])
        fh.flush(); os.fsync(fh.fileno())
        print(f"   template violations {bad}, subset {size} numbers -> {res}  =>  {verdict}   ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()

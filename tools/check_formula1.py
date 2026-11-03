# -*- coding: utf-8 -*-
r"""Formula 1 (R3(a(x-y)=bz) = b^3+b^2+(2a+1)b+1) - the lower-bound colouring found 2026-10-29 from the 16 examples of 57:
   n = b^3+b^2+(2a+1)b (= R-1)
   C0: a does not divide x and x <= ab-1  |  a^2 | x and x <= b a^2  |  every x > n - ab   (end block)
   C1: a | x, x <= ab(b+1), not in C0
   C2: the rest
Conjecture (golden ratio): the colouring is valid  <=>  a^2 + (b-1)a <= b^2 + b + 1  (a <= (1-b+sqrt(5b^2+2b+5))/2 = 0.618b+0.72...).
For every b in [bmin,bmax] and every 2 <= a < b with gcd(a,b)=1 it counts the monochromatic solutions (all of them, numpy),
for all a inside the region and the first 3 a outside.  One row per cell in results\formula1_template.csv (skipped on restart,
Ctrl+C is safe).  Run: python tools\check_formula1.py 5 60"""
import csv, math, os, sys, time
from datetime import datetime, timezone, timedelta
import numpy as np
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "formula1_template.csv")


def colour(a, b, n):
    x = np.arange(n + 1, dtype=np.int64); a1 = (x % a == 0); a2 = (x % (a * a) == 0)
    c = np.full(n + 1, 2, np.int8)
    c[a1 & (x <= a * b * (b + 1))] = 1
    c[(~a1) & (x <= a * b - 1)] = 0
    c[a2 & (x <= b * a * a)] = 0
    c[x > n - a * b] = 0
    return c


def violations(a, b, n, c):
    s, tot, first = 1, 0, ""
    while b * s <= n - 1 and a * s <= n:
        d, z = b * s, a * s
        y = np.arange(1, n - d + 1)
        m = (c[y] == c[y + d]) & (c[y] == c[z]); k = int(m.sum())
        if k and not first:
            yy = int(y[m][0]); first = f"y={yy} x={yy + d} z={z}"
        tot += k; s += 1
    return tot, first


def main():
    bmin, bmax = int(sys.argv[1]), int(sys.argv[2])
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["a"]), int(r["b"])))
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "n", "in_region", "violations", "first", "seconds"])
    agree = disagree = 0
    for b in range(bmin, bmax + 1):
        outside = 0
        for a in range(2, b):
            if math.gcd(a, b) != 1: continue
            inside = a * a + (b - 1) * a <= b * b + b + 1
            if not inside:
                outside += 1
                if outside > 3: break
            if (a, b) in done: continue
            n = b ** 3 + b * b + (2 * a + 1) * b
            t = time.time(); k, first = violations(a, b, n, colour(a, b, n))
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), a, b, n, int(inside), k, first, round(time.time() - t, 1)])
            fh.flush(); os.fsync(fh.fileno())
            ok = (k == 0) == inside
            agree += ok; disagree += (not ok)
            print(f"({a},{b}) n={n} region={'in ' if inside else 'out'} violations={k} {'OK' if ok else '<-- DIFFERENT'}", flush=True)
    print(f"this run: agree {agree}, different {disagree}  (all rows: results\\formula1_template.csv)")


if __name__ == "__main__":
    main()

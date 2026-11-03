# -*- coding: utf-8 -*-
r"""Generalizer-mode evaluator: a RULE (a python file in rules\ with colour(x, a, b, n, j) -> 0/1/2) is scored on many b at
once: for every b, the number of monochromatic solutions of a(x-y)=bz in [1,n], n = b^3+2b^2-j^2(j+2)-1, a = b-j, and the
first violating triples with their features (valuation, x/a^v, residues).  0 for all b = a candidate for a proof.
Results are appended to results\rule_scores.csv (one row per rule and b; rows already there are skipped; Ctrl+C is safe).
Run: python tools\eval_rule.py rules\j3_template.py 3 13 16 19 ... (rule file, j, values of b)"""
import csv, importlib.util, math, os, sys, time
from datetime import datetime, timezone, timedelta
import numpy as np
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "rule_scores.csv")


def va(x, a):
    e = 0
    while x % a == 0:
        x //= a; e += 1
    return e


def main():
    path, j = sys.argv[1], int(sys.argv[2]); bs = [int(x) for x in sys.argv[3:]]
    spec = importlib.util.spec_from_file_location("rule", path); rule = importlib.util.module_from_spec(spec); spec.loader.exec_module(rule)
    name = os.path.basename(path)
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((r["rule"], r["j"], r["b"]))
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "rule", "j", "b", "n", "violations", "seconds", "first_violations"])
    for b in bs:
        a = b - j
        if a < 2 or math.gcd(a, b) != 1 or (name, str(j), str(b)) in done: continue
        n = b ** 3 + 2 * b * b - j * j * (j + 2) - 1
        t0 = time.time()
        col = np.zeros(n + 1, dtype=np.int8)
        for x in range(1, n + 1): col[x] = rule.colour(x, a, b, n, j)
        bad = 0; ex = []; s = 1
        while b * s <= n - 1 and a * s <= n:
            d = b * s; z = a * s; y = np.arange(1, n - d + 1)
            m = (col[y] == col[y + d]) & (col[y] == col[z])
            c = int(m.sum()); bad += c
            if c and len(ex) < 5:
                for yy in y[m][:5 - len(ex)]:
                    yy = int(yy); xx = yy + d
                    ex.append(f"s={s} y={yy}(v{va(yy,a)},y-ab={yy-a*b}) x={xx}(v{va(xx,a)},n-x={n-xx},x/a={xx/a:.1f}) z={z}(v{va(z,a)},z/a^2={z/a/a:.2f}) col={int(col[z])}")
            s += 1
        print(f"{name} j={j} b={b} n={n}: violations {bad} ({time.time()-t0:.0f}s)", flush=True)
        for e in ex: print("    ", e, flush=True)
        w.writerow([f"{datetime.now(JST):%Y-%m-%d %H:%M:%S}", name, j, b, n, bad, round(time.time() - t0, 1), " | ".join(ex)]); fh.flush(); os.fsync(fh.fileno())


if __name__ == "__main__":
    main()

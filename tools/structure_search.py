# -*- coding: utf-8 -*-
r"""Find the most "regular" extremal 3-colouring for j=2 (a=b-2, n=b^3+2b^2-17 = R-1) as a TEMPLATE + few EXCEPTIONS.
Colours (first-fit): 0 = colour of 1, 1 = colour of the numbers with v_a = 1 and m <= b(b+1), 2 = the main colour of the units.
HARD: the Rado CNF + level-1 rule found on 2026-10-28 (x = a*m, a does not divide m: colour 1 if m <= b(b+1), else colour 2).
SOFT (weight 1 each): every unit x (a does not divide x) gets its template colour: 0 if x <= A or x >= B, else 2;
   A = a*b - 1 (seen in (15,17), (17,19)), B = n - B_off (B_off from the command line, default 2b).
MaxSAT (pysat RC2) returns a colouring with the FEWEST units off the template -> the exceptions are printed and saved.
Also prints the colours of the numbers with v_a >= 2. One cell at a time, results in results\structure\a{a}_b{b}.json
(skipped if present; Ctrl+C is safe).  Run: python tools\structure_search.py 17 19 21 23   (values of b)"""
import json, os, sys, time
from datetime import datetime, timezone, timedelta
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
JST = timezone(timedelta(hours=9))
OUT = os.path.join(HERE, "..", "results", "structure")


def va(x, a):
    e = 0
    while x % a == 0:
        x //= a; e += 1
    return e


def run(b, boff):
    from pysat.formula import WCNF
    from pysat.examples.rc2 import RC2
    from rado_c1 import iter_cnf
    a = b - 2; k = 3; n = b ** 3 + 2 * b * b - 17
    A = a * b - 1; B = n - boff
    v = lambda j, c: (j - 1) * k + c + 1
    w = WCNF()
    for c in iter_cnf(a, b, k, n):
        w.append(c)
    for x in range(1, n + 1):
        t = va(x, a)
        if t == 1:
            w.append([v(x, 1)] if x // a <= b * (b + 1) else [v(x, 2)])
        elif t == 0:
            w.append([-v(x, 1)])                                  # units never use colour 1
            w.append([v(x, 0) if (x <= A or x >= B) else v(x, 2)], weight=1)
    t0 = time.time()
    with RC2(w, solver="m22") as r:
        m = r.compute()
        cost = r.cost
    if m is None:
        return {"a": a, "b": b, "n": n, "status": "UNSAT (template/level rule impossible)"}
    pos = set(l for l in m if l > 0)
    col = [next(c for c in range(k) if v(j, c) in pos) for j in range(1, n + 1)]
    exc = [(x, col[x - 1]) for x in range(1, n + 1) if va(x, a) == 0 and col[x - 1] != (0 if (x <= A or x >= B) else 2)]
    high = [(x, x // (a * a), col[x - 1]) for x in range(1, n + 1) if va(x, a) >= 2]
    return {"a": a, "b": b, "n": n, "A": A, "B": B, "exceptions": exc, "n_exceptions": cost, "high_levels": high,
            "seconds": round(time.time() - t0, 1), "jst_time": f"{datetime.now(JST):%Y-%m-%d %H:%M:%S}", "coloring": col}


def main():
    os.makedirs(OUT, exist_ok=True)
    bs = [int(x) for x in sys.argv[1:]] or [17, 19, 21, 23, 25]
    for b in bs:
        path = os.path.join(OUT, f"a{b-2}_b{b}.json")
        if os.path.exists(path): continue
        print(f"[{datetime.now(JST):%Y-%m-%d %H:%M:%S} JST] b={b} ...", flush=True)
        res = run(b, 2 * b)
        if "exceptions" in res:
            print(f"   {res['n_exceptions']} exceptions in {res['seconds']}s: {res['exceptions'][:40]}", flush=True)
            print(f"   v_a>=2 (x, x/a^2, colour): {res['high_levels']}", flush=True)
        else:
            print("  ", res["status"], flush=True)
        tmp = path + ".tmp"; json.dump(res, open(tmp, "w", encoding="utf-8")); os.replace(tmp, path)


if __name__ == "__main__":
    main()

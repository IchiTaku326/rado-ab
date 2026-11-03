# -*- coding: utf-8 -*-
r"""General version of structure_search.py for a = b - j (conjecture C: R3 >= N - j^2(j+2), N = b^3+2b^2).
Target n = N - j^2(j+2) - 1 (the lower bound).  MaxSAT (pysat RC2): hard = Rado CNF; SOFT = the j=2 template
(the theorem of 2026-10-28), every number separately:
  v=0: colour 0 if x <= ab-1 or x >= n-2b, else 2 | v=1: colour 1 if x <= ab(b+1), else 2 |
  v>=2: colour 0 if x/a^2 <= b, 1 if <= b+3, else 2
The result = a colouring with the fewest numbers off the template; the exceptions are printed by type.
Results: results\structure\j{j}_a{a}_b{b}.json (skipped if present; Ctrl+C is safe).
Run: python tools\structure_search2.py J b1 b2 ...   (keep n below about 20000: the WCNF is held in Python memory)"""
import json, math, os, sys, time
from datetime import datetime, timezone, timedelta
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
JST = timezone(timedelta(hours=9))
OUT = os.path.join(HERE, "..", "results", "structure")


def va(x, a):
    e = 0
    while x % a == 0:
        x //= a; e += 1
    return e


def template(x, a, b, n):
    t = va(x, a)
    if t == 0: return 0 if (x <= a * b - 1 or x >= n - 2 * b) else 2
    if t == 1: return 1 if x <= a * b * (b + 1) else 2
    q = x // (a * a)
    return 0 if q <= b else (1 if q <= b + 3 else 2)


def run(j, b):
    from pysat.formula import WCNF
    from pysat.examples.rc2 import RC2
    from rado_c1 import iter_cnf
    a = b - j; k = 3; n = b ** 3 + 2 * b * b - j * j * (j + 2) - 1
    v = lambda i, c: (i - 1) * k + c + 1
    w = WCNF()
    for c in iter_cnf(a, b, k, n):
        w.append(c)
    for x in range(1, n + 1):
        w.append([v(x, template(x, a, b, n))], weight=1)
    t0 = time.time()
    with RC2(w, solver="m22") as r:
        m = r.compute(); cost = r.cost
    if m is None:
        return {"j": j, "a": a, "b": b, "n": n, "status": "UNSAT: n is NOT colourable (conjecture C lower bound fails here)"}
    pos = set(l for l in m if l > 0)
    col = [next(c for c in range(k) if v(i, c) in pos) for i in range(1, n + 1)]
    exc = {"v0": [], "v1": [], "v2+": []}
    for x in range(1, n + 1):
        tc = template(x, a, b, n)
        if col[x - 1] != tc:
            t = va(x, a)
            key = "v0" if t == 0 else ("v1" if t == 1 else "v2+")
            info = (x, col[x - 1]) if t == 0 else ((x, x // a, col[x - 1]) if t == 1 else (x, x // (a * a), col[x - 1]))
            exc[key].append(info)
    return {"j": j, "a": a, "b": b, "n": n, "exceptions": exc, "n_exceptions": cost,
            "seconds": round(time.time() - t0, 1), "jst_time": f"{datetime.now(JST):%Y-%m-%d %H:%M:%S}", "coloring": col}


def main():
    j = int(sys.argv[1]); bs = [int(x) for x in sys.argv[2:]]
    os.makedirs(OUT, exist_ok=True)
    for b in bs:
        a = b - j
        if a < 2 or math.gcd(a, b) != 1: continue
        path = os.path.join(OUT, f"j{j}_a{a}_b{b}.json")
        if os.path.exists(path): continue
        print(f"[{datetime.now(JST):%Y-%m-%d %H:%M:%S} JST] j={j} b={b} a={a} ...", flush=True)
        res = run(j, b)
        if "exceptions" in res:
            e = res["exceptions"]
            print(f"   {res['n_exceptions']} off the template ({res['seconds']}s)  v0: {len(e['v0'])}  v1: {len(e['v1'])}  v2+: {len(e['v2+'])}", flush=True)
            for key in ("v0", "v1", "v2+"):
                if e[key]: print(f"     {key}: {e[key][:30]}{' ...' if len(e[key]) > 30 else ''}", flush=True)
        else:
            print("  ", res["status"], flush=True)
        tmp = path + ".tmp"; json.dump(res, open(tmp, "w", encoding="utf-8")); os.replace(tmp, path)


if __name__ == "__main__":
    main()

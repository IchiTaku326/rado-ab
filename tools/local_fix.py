# -*- coding: utf-8 -*-
r"""Where must the template change?  Fix the template colour of every number EXCEPT the numbers in the given free windows
(units near the start block, units near the end block, the v>=2 numbers with u near b+h), solve with MiniSat (streaming),
and print the colours the solver chose in the free windows.  For j=3 the template fails at b=43, 44 (found 2026-10-28).
Run: python tools\local_fix.py J H b    (e.g. 3 4 43).  Result: results\structure\localfix_j{J}_b{b}.json (skipped if present)."""
import json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)


def va(x, a):
    e = 0
    while x % a == 0:
        x //= a; e += 1
    return e


def main():
    j, h, b = map(int, sys.argv[1:4])
    tag = "_wide" if "--wide" in sys.argv else ""
    a = b - j; n = b ** 3 + 2 * b * b - j * j * (j + 2) - 1; k = 3
    out = os.path.join(HERE, "..", "results", "structure", f"localfix_j{j}_b{b}{tag}.json")
    if os.path.exists(out): print("done already:", out); return
    from pysat.solvers import Solver
    from rado_c1 import iter_cnf
    v = lambda i, c: (i - 1) * k + c + 1
    def tmpl(x):
        t = va(x, a)
        if t == 0: return 0 if (x <= a * b - 1 or x >= n - 2 * b) else 2
        if t == 1: return 1 if x // a <= b * (b + 1) else 2
        u = x // (a * a); return 0 if u <= b else (1 if u <= b + h else 2)
    wide = "--wide" in sys.argv
    free = lambda x: (a * b - 3 * b <= x <= a * b + 3 * b) or (x >= n - 6 * b) or (va(x, a) >= 2 and abs(x // (a * a) - (b + h)) <= 3) \
        or (wide and va(x, a) == 1 and abs(x // a - b * (b + 1)) <= 3 * b) or (wide and va(x, a) == 0 and x <= a * b + 3 * b)
    t0 = time.time()
    with Solver(name="minisat22") as S:
        for c in iter_cnf(a, b, k, n): S.add_clause(c)
        nfree = 0
        for x in range(1, n + 1):
            if free(x): nfree += 1; continue
            S.add_clause([v(x, tmpl(x))])
        ok = S.solve()
        res = {"j": j, "h": h, "b": b, "a": a, "n": n, "free_numbers": nfree, "sat": bool(ok), "seconds": round(time.time() - t0, 1)}
        if ok:
            pos = set(l for l in S.get_model() if l > 0)
            col = {x: next(c for c in range(k) if v(x, c) in pos) for x in range(1, n + 1) if free(x)}
            res["changed"] = [(x, va(x, a), tmpl(x), col[x]) for x in sorted(col) if col[x] != tmpl(x)]
    print(json.dumps({kk: vv for kk, vv in res.items() if kk != "changed"}))
    if res.get("sat"):
        print("numbers whose colour differs from the template (x, v_a(x), template, chosen):")
        for row in res["changed"]: print("  ", row)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out + ".tmp", "w")); os.replace(out + ".tmp", out)


if __name__ == "__main__":
    main()

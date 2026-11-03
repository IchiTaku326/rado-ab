# -*- coding: utf-8 -*-
r"""Data for "generalizer mode" (find ONE rule that works for all b): a valid colouring of [1,n], n = N - j^2(j+2) - 1,
that stays as close as possible to the template, cheaply: MiniSat with its PHASES set to the template colours
(the solver tries the template colour first; no MaxSAT, no big Python clause list).  Saves the colouring and the
list of numbers that differ from the template, with features (v_a, x/a^v, x mod a, x mod b, position).
Run: python tools\phase_coloring.py J H E b    (E: end block of units = n - E*b).  Result results\structure\phase_j{J}_b{b}.json"""
import json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)


def va(x, a):
    e = 0
    while x % a == 0:
        x //= a; e += 1
    return e


def main():
    j, h, E, b = map(int, sys.argv[1:5])
    free_a = "--free-a" in sys.argv          # do NOT force a to colour 1 (only 1 -> colour 0, which is no loss of generality)
    a = b - j; n = b ** 3 + 2 * b * b - j * j * (j + 2) - 1; k = 3
    nset = [int(t.split("=")[1]) for t in sys.argv if t.startswith("--n=")]
    if nset: n = nset[0]                     # e.g. --n=83119 (= R-1 when the conjecture-C size is not colourable)
    out = os.path.join(HERE, "..", "results", "structure", f"phase_j{j}_b{b}{'_freea' if free_a else ''}{('_n' + str(n)) if nset else ''}.json")
    if os.path.exists(out): print("done already:", out); return
    from pysat.solvers import Solver
    from rado_c1 import iter_cnf
    v = lambda i, c: (i - 1) * k + c + 1
    def tmpl(x):
        t = va(x, a)
        if t == 0: return 0 if (x <= a * b - 1 or x >= n - E * b) else 2
        if t == 1: return 1 if x // a <= b * (b + 1) else 2
        u = x // (a * a); return 0 if u <= b else (1 if u <= b + h else 2)
    t0 = time.time()
    with Solver(name="minisat22") as S:
        for c in iter_cnf(a, b, k, n, symbreak=False): S.add_clause(c)   # no symmetry clauses: colours keep the template's meaning
        S.add_clause([v(1, 0)])                                          # fix the colour names: 1 -> 0, a -> 1
        if not free_a: S.add_clause([v(a, 1)])
        else: S.add_clause([-v(a, 0), -v(2, 0)] if False else [v(1, 0)])   # placeholder (1 -> 0 already); colours 1 and 2 stay symmetric
        S.set_phases([v(x, c) if c == tmpl(x) else -v(x, c) for x in range(1, n + 1) for c in range(k)])
        ok = S.solve()
        res = {"j": j, "h": h, "E": E, "b": b, "free_a": free_a, "a": a, "n": n, "sat": bool(ok), "seconds": round(time.time() - t0, 1)}
        if ok:
            pos = set(l for l in S.get_model() if l > 0)
            col = [next(c for c in range(k) if v(x, c) in pos) for x in range(1, n + 1)]
            diff = []
            for x in range(1, n + 1):
                if col[x - 1] != tmpl(x):
                    t = va(x, a)
                    diff.append({"x": x, "v": t, "q": x // a ** t, "x_mod_a": x % a, "x_mod_b": x % b, "from_end": n - x,
                                 "template": tmpl(x), "colour": col[x - 1]})
            res["n_diff"] = len(diff); res["diff"] = diff; res["coloring"] = col
    print(json.dumps({kk: vv for kk, vv in res.items() if kk not in ("diff", "coloring")}))
    if res.get("sat"):
        from collections import Counter
        print("differences by (v, template -> colour):", dict(Counter((d["v"], d["template"], d["colour"]) for d in res["diff"])))
        for d in res["diff"][:60]: print("  ", d)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out + ".tmp", "w")); os.replace(out + ".tmp", out)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
r"""Look for structure in the colourings of results\colorings (made by collect_colorings.py): for each file, the colours
of the numbers by a-adic valuation and by divisibility by b, and the colour runs of the numbers not divisible by a
(as intervals, also written relative to a, b).  Writes results\colorings\ANALYSIS.txt.  Run: python tools\analyze_colorings.py"""
import glob, json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "results", "colorings")


def va(x, a):
    e = 0
    while x % a == 0:
        x //= a; e += 1
    return e


def main():
    lines = []
    for p in sorted(glob.glob(os.path.join(D, "a*_b*_k3_n*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        a, b, n, col = d["a"], d["b"], d["n"], d["coloring"]
        j = b - a
        lines.append(f"== a={a} b={b} j={j} n={n} (R={n+1}, N-R={b*b*(b+2)-n-1})")
        tab = collections.defaultdict(collections.Counter)
        for x in range(1, n + 1):
            tab[(va(x, a), x % b == 0)][col[x - 1]] += 1
        for key in sorted(tab):
            lines.append(f"   v_a={key[0]} b|x={key[1]}: {dict(tab[key])}")
        runs = []
        for x in range(1, n + 1):
            if x % a == 0: continue
            if runs and runs[-1][2] == col[x - 1]: runs[-1][1] = x
            else: runs.append([x, x, col[x - 1]])
        big = [r for r in runs if r[1] - r[0] >= a]   # long runs only
        lines.append(f"   units (a does not divide x): {len(runs)} runs, {len(big)} of length >= a:")
        for s, e, c in big[:40]:
            lines.append(f"      [{s}, {e}] colour {c}   (start/a^2={s/a/a:.2f}, end/a^2={e/a/a:.2f}, len={e-s+1})")
    out = os.path.join(D, "ANALYSIS.txt")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:80])); print("... written", out)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
r"""Item 3 experiment (2026-11-02 JST): k-colour [1,n] for a(x-y)=bz where non-multiples of a share a colour per block x//B
and multiples of a are free.  CaDiCaL (bin_linux, WSL) with a time limit; a SAT answer is checked directly and saved as
results\c1_k4ab\cert_a{a}_b{b}_k{k}_n{n}_multfree.json.   Run: python tools\research\mult_free_sat.py a b k n B seconds"""
import sys, subprocess, os, json, tempfile
a, b, k, n, B, T = map(int, sys.argv[1:7])
key = lambda x: ("m", x) if x % a == 0 else ("b", x // B)
keys = sorted({key(x) for x in range(1, n + 1)}); kid = {kk: i for i, kk in enumerate(keys)}
v = lambda x, c: k * kid[key(x)] + c + 1
cls = set()
for i in range(len(keys)):
    cls.add(tuple(k * i + c + 1 for c in range(k)))
    for c in range(k):
        for d in range(c + 1, k): cls.add((-(k * i + c + 1), -(k * i + d + 1)))
for z in range(1, n + 1):
    if (b * z) % a: continue
    dlt = b * z // a
    for y in range(1, n - dlt + 1):
        x = y + dlt
        for c in range(k): cls.add(tuple(sorted({-v(x, c), -v(y, c), -v(z, c)})))
f = tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False)
f.write(f"p cnf {k*len(keys)} {len(cls)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in cls)); f.close()
print(f"vars {k*len(keys)} clauses {len(cls)}", flush=True)
cb = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bin_linux", "cadical")
r = subprocess.run([cb, "-t", str(T), "-q", f.name], capture_output=True, text=True)
os.unlink(f.name)
if "s SATISFIABLE" not in r.stdout: print("result:", "UNSAT" if "UNSAT" in r.stdout else "UNKNOWN (time limit)"); sys.exit()
val = set(int(t) for line in r.stdout.splitlines() if line.startswith("v") for t in line.split()[1:] if int(t) > 0)
col = [next(c for c in range(k) if v(x, c) in val) for x in range(1, n + 1)]
for z in range(1, n + 1):
    if (b * z) % a == 0:
        dlt = b * z // a
        for y in range(1, n - dlt + 1):
            assert not (col[y - 1] == col[y + dlt - 1] == col[z - 1]), (y + dlt, y, z)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "c1_k4ab", f"cert_a{a}_b{b}_k{k}_n{n}_multfree.json")
json.dump({"a": a, "b": b, "k": k, "n": n, "coloring": col, "method": f"multfree B={B}"}, open(out, "w"))
print("result: SAT, checked directly, saved", out)

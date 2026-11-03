"""Lemma S experiment on the reduced chain+copy system (main region).
For (a,b): R2=b^2+b+1, T=R2+2a, chain positions t=0..L-1 (number 1+bt), copy m=1..R2 (number a*m).
Assume phi(s0)=phi(R2) and check UNSAT; optionally compute a minimal core over elements.
"""
import subprocess, sys, os, tempfile, itertools
CAD = "/home/claude/bin/cadical"

def build(a, b, L, R2=None):
    R2 = R2 or b*b+b+1
    num = {}   # number -> element id
    elems = []
    def el(n, tag):
        if n not in num:
            num[n] = len(elems); elems.append((n, [tag]))
        else:
            elems[num[n]][1].append(tag)
        return num[n]
    copy = {m: el(a*m, ('m', m)) for m in range(1, R2+1)}
    chain = {t: el(1+b*t, ('t', t)) for t in range(L)}
    sols = set()
    for s in range(1, R2+1):
        for Y in range(1, R2+1):
            X = Y + b*s
            if X > R2: break
            if a*s <= R2:
                sols.add(tuple(sorted({copy[X], copy[Y], copy[a*s]})) if False else (copy[X], copy[Y], copy[a*s]))
    for t in range(L):
        for u in range(t+1, min(L, t+R2+1)):
            sols.add((chain[u], chain[t], copy[u-t]))
    return elems, copy, chain, sorted(sols)

def solve(nE, sols, fixed, keep, K=3, model=False):
    v = lambda e, c: e*K + c + 1
    cl = []
    for e in range(nE):
        if e in keep:
            cl.append([v(e, c) for c in range(K)])
            for c1, c2 in itertools.combinations(range(K), 2):
                cl.append([-v(e, c1), -v(e, c2)])
    for (x, y, z) in sols:
        if x in keep and y in keep and z in keep:
            for c in range(K):
                cl.append(sorted({-v(x, c), -v(y, c), -v(z, c)}))
    cl += fixed(v)
    with tempfile.NamedTemporaryFile('w', suffix='.cnf', delete=False) as f:
        f.write(f"p cnf {nE*K} {len(cl)}\n")
        for c in cl: f.write(" ".join(map(str, c)) + " 0\n")
        fn = f.name
    r = subprocess.run([CAD, "-q", fn], capture_output=True, text=True)
    os.unlink(fn)
    if r.returncode == 20: return None
    vals = set()
    for line in r.stdout.split("\n"):
        if line.startswith("v"): vals |= {int(x) for x in line.split()[1:] if int(x) > 0}
    return {e: next(c for c in range(K) if v(e, c) in vals) for e in range(nE) if e in keep}

def eqfix(e1, e2, sym_e=None):
    def f(v):
        out = []
        for c in range(3):
            out.append([-v(e1, c), v(e2, c)]); out.append([v(e1, c), -v(e2, c)])
        if sym_e is not None: out.append([v(sym_e, 0)])
        return out
    return f

def core(nE, sols, fixed, must):
    keep = set(range(nE))
    for e in sorted(range(nE), reverse=True):
        if e in must: continue
        trial = keep - {e}
        if solve(nE, sols, fixed, trial) is None: keep = trial
    return keep

if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2])
    R2 = b*b+b+1; T = R2+2*a
    elems, copy, chain, sols = build(a, b, T)
    nE = len(elems)
    allk = set(range(nE))
    print(f"(a,b)=({a},{b}) R2={R2} T={T} elems={nE} sols={len(sols)}")
    # sanity: SAT without the assumption
    print("free SAT:", solve(nE, sols, eqfix(copy[R2], copy[R2]), allk) is not None)
    bad = [s0 for s0 in range(1, R2) if solve(nE, sols, eqfix(copy[s0], copy[R2]), allk) is not None]
    print("s0 with phi(s0)=phi(R2) satisfiable:", bad)

"""Induction-step test: fix phi on [1,K] to the 2-colour pattern T2 (a*u, u<=b -> colour 0; others -> colour 1),
full chain (length T), ask whether phi(K+1) is forced to its pattern colour (the other two colours UNSAT)."""
import sys
from lemS import *
a,b=int(sys.argv[1]),int(sys.argv[2]); R2=b*b+b+1; T=R2+2*a
Lc=int(sys.argv[3]) if len(sys.argv)>3 else T
elems,copy,chain,sols=build(a,b,T); nE=len(elems)
keep={copy[m] for m in range(1,R2+1)}|{chain[t] for t in range(Lc)}
pat=lambda m: 0 if (m%a==0 and m//a<=b) else (1 if m<=b*b+b else 2)
fail=[]
for K in range(0,R2-1):
    want=pat(K+1)
    bad=[]
    for c in range(3):
        if c==want: continue
        def f(v,K=K,c=c):
            out=[[v(copy[m],pat(m))] for m in range(1,K+1)]
            out.append([v(copy[K+1],c)])
            return out
        if solve(nE,sols,f,keep) is not None: bad.append(c)
    if bad: fail.append((K+1,want,bad))
print(f"({a},{b}) chain L={Lc}: step fails at (m, pattern colour, colours still possible): {fail}")

import sys
from lemS import *
a,b=int(sys.argv[1]),int(sys.argv[2]); R2=b*b+b+1; T=R2+2*a
elems,copy,chain,sols=build(a,b,T); nE=len(elems)
pat=lambda m: 0 if (m%a==0 and m//a<=b) else (1 if m<=b*b+b else 2)
for spec in sys.argv[3:]:
    m0,c=map(int,spec.split(':'))
    fixed={copy[m] for m in range(1,R2+1) if m!=m0}
    def f(v,keep=None):
        return [[v(copy[m],pat(m))] for m in range(1,R2+1) if m!=m0 and copy[m] in (keep if keep else fixed)]+[[v(copy[m0],c)]]
    keep=set(range(nE))
    if solve(nE,sols,lambda v:f(v,keep),keep) is not None: print(m0,c,"SAT even with everything fixed"); continue
    for e in sorted(range(nE),reverse=True):
        if e==copy[m0]: continue
        tr=keep-{e}
        if solve(nE,sols,lambda v:f(v,tr),tr) is None: keep=tr
    ts=sorted(t[1] for e in keep for t in elems[e][1] if t[0]=='t')
    ms=sorted(t[1] for e in keep for t in elems[e][1] if t[0]=='m')
    print(f"m={m0} colour {c} (rest = pattern): chain {ts}  copy {ms}",flush=True)

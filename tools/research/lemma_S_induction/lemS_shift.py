import sys
from lemS import *
def run(a,b):
    R2=b*b+b+1; T=R2+2*a
    elems,copy,chain,sols=build(a,b,T); nE=len(elems)
    pat=lambda m: 0 if (m%a==0 and m//a<=b) else (1 if m<=b*b+b else 2)
    t0=next(t for t in range(a) if (1+b*t)%a==0)
    copyset={copy[m] for m in range(1,R2+1)}
    spec={t for t in range(T) if t%a==t0}
    res=[]
    for m0 in range(a+1,R2):
        K=m0-1; want=pat(m0)
        for c in range(3):
            if c==want: continue
            f=lambda v,c=c:[[v(copy[m],pat(m))] for m in range(1,K+1)]+[[v(copy[m0],c)]]
            if solve(nE,sols,f,copyset) is None: continue
            ok=None
            for q in range(0,T-m0-2*a):
                W={q,q+a,q+2*a,q+m0,q+m0+a,q+m0+2*a}|spec
                if solve(nE,sols,f,copyset|{chain[t] for t in W}) is None: ok=q; break
            if ok is None or ok>0: res.append((m0,c,ok))
    print(f"({a},{b}) steps needing shift q>0 or not W at all (m,colour,q or None): {res}",flush=True)
for p in sys.argv[1:]: run(*map(int,p.split(',')))

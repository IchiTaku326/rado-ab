import sys
from lemS import *
def run(a,b):
    R2=b*b+b+1; T=R2+2*a
    elems,copy,chain,sols=build(a,b,T); nE=len(elems)
    pat=lambda m: 0 if (m%a==0 and m//a<=b) else (1 if m<=b*b+b else 2)
    t0=next(t for t in range(a) if (1+b*t)%a==0)
    copyset={copy[m] for m in range(1,R2+1)}
    A={a*u2+b*u for u in range(1,b+1) for u2 in range(1,b+1)}
    hard=[]; stats={'copy':0,'W':0,'hard':0}
    for m0 in range(a+1,R2):
        K=m0-1; want=pat(m0)
        for c in range(3):
            if c==want: continue
            f=lambda v,c=c:[[v(copy[m],pat(m))] for m in range(1,K+1)]+[[v(copy[m0],c)]]
            if solve(nE,sols,f,copyset) is None: stats['copy']+=1; continue
            W={0,a,2*a,m0,m0+a,m0+2*a}|{t for t in range(min(T,m0+2*a+1)) if t%a==t0}
            if solve(nE,sols,f,copyset|{chain[t] for t in W if t<T}) is None: stats['W']+=1; continue
            stats['hard']+=1
            kind='a*u' if m0%a==0 and m0//a<=b else ('inA' if m0 in A else 'notA')
            hard.append((m0,c,kind))
    print(f"({a},{b}) steps: {stats}\n   hard (m, excluded colour, type): {hard}",flush=True)
for p in sys.argv[1:]: run(*map(int,p.split(',')))

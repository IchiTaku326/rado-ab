import sys
from lemS import *
a,b=int(sys.argv[1]),int(sys.argv[2]); R2=b*b+b+1; T=R2+2*a
elems,copy,chain,sols=build(a,b,T); nE=len(elems)
pat=lambda m: 0 if (m%a==0 and m//a<=b) else (1 if m<=b*b+b else 2)
for m0 in [int(x) for x in sys.argv[3].split(',')]:
    K=m0-1; want=pat(m0)
    fixed_el={copy[m] for m in range(1,K+1)}
    for c in range(3):
        if c==want: continue
        f=lambda v,c=c:[[v(copy[m],pat(m))] for m in range(1,K+1)]+[[v(copy[m0],c)]]
        keep=set(range(nE))
        for e in sorted(range(nE),reverse=True):
            if e in fixed_el or e==copy[m0]: continue
            tr=keep-{e}
            if solve(nE,sols,f,tr) is None: keep=tr
        # which fixed copy elements are actually used? test removing each
        used=set(keep)
        for e in sorted(fixed_el):
            tr=used-{e}
            f2=lambda v,c=c,tr=tr:[[v(copy[m],pat(m))] for m in range(1,K+1) if copy[m] in tr]+[[v(copy[m0],c)]]
            if solve(nE,sols,f2,tr) is None: used=tr
        ts=sorted(t[1] for e in used for t in elems[e][1] if t[0]=='t')
        ms=sorted(t[1] for e in used for t in elems[e][1] if t[0]=='m')
        print(f"m={m0} (pattern {want}) colour {c} impossible: chain {ts}  copy {ms}",flush=True)

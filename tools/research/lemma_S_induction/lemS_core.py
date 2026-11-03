import sys
from lemS import *
a,b=int(sys.argv[1]),int(sys.argv[2]); s0s=[int(x) for x in sys.argv[3].split(',')]
R2=b*b+b+1; T=R2+2*a
elems,copy,chain,sols=build(a,b,T); nE=len(elems)
for s0 in s0s:
    fx=eqfix(copy[s0],copy[R2])
    k=core(nE,sols,fx,{copy[s0],copy[R2]})
    ms=sorted(t[1] for e in k for t in elems[e][1] if t[0]=='m')
    ts=sorted(t[1] for e in k for t in elems[e][1] if t[0]=='t')
    print(f"s0={s0}: |core|={len(k)}  copy m={ms}\n   chain t={ts}",flush=True)

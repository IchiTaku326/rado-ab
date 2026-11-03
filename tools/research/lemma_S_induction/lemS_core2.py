import sys
from lemS import *
a,b=int(sys.argv[1]),int(sys.argv[2]); R2=b*b+b+1
for s0,L in [tuple(map(int,x.split(':'))) for x in sys.argv[3:]]:
    elems,copy,chain,sols=build(a,b,L); nE=len(elems)
    fx=eqfix(copy[s0],copy[R2])
    k=core(nE,sols,fx,{copy[s0],copy[R2]})
    ms=sorted(t[1] for e in k for t in elems[e][1] if t[0]=='m')
    ts=sorted(t[1] for e in k for t in elems[e][1] if t[0]=='t')
    print(f"s0={s0} L={L}: |core|={len(k)} copy m={ms}\n   chain t={ts}",flush=True)

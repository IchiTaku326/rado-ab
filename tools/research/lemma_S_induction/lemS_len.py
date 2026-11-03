import sys
from lemS import *
def Lstar(a,b):
    R2=b*b+b+1; T=R2+2*a
    res={}
    elems,copy,chain,sols=build(a,b,T); nE=len(elems)
    # binary search per s0 over chain length L (monotone: longer chain = more constraints)
    def unsat(s0,L):
        keep={copy[m] for m in range(1,R2+1)}|{chain[t] for t in range(L)}
        return solve(nE,sols,eqfix(copy[s0],copy[R2]),keep) is None
    for s0 in range(1,R2):
        if not unsat(s0,T): res[s0]=None; continue
        lo,hi=0,T
        while lo<hi:
            mid=(lo+hi)//2
            if unsat(s0,mid): hi=mid
            else: lo=mid+1
        res[s0]=lo
    return R2,T,res
for p in sys.argv[1:]:
    a,b=map(int,p.split(','))
    R2,T,res=Lstar(a,b)
    vals=[v for v in res.values() if v is not None]
    worst=max(vals); arg=[s for s,v in res.items() if v==worst]
    zero=[s for s,v in res.items() if v==0]
    print(f"({a},{b}) R2={R2} T={T}: max L*={worst} at s0={arg}; L*=0 (copy alone) for {len(zero)} of {R2-1} s0; none-UNSAT: {[s for s,v in res.items() if v is None]}",flush=True)
    print("   L* by s0:",{s:v for s,v in res.items() if v and v>worst-6})

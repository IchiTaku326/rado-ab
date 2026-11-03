import sys
from lemS import *
def neq(e1,e2):
    def f(v):
        return [[-v(e1,c),-v(e2,c)] for c in range(3)]
    return f
a,b=int(sys.argv[1]),int(sys.argv[2]); R2=b*b+b+1; T=R2+2*a
elems,copy,chain,sols=build(a,b,T); nE=len(elems)
for L in [int(x) for x in sys.argv[3].split(',')]:
    keep={copy[m] for m in range(1,R2+1)}|{chain[t] for t in range(L)}
    A=[];B=[];free=[]
    for m in range(2,R2+1):
        f1 = solve(nE,sols,neq(copy[m],copy[1]),keep) is None   # forced phi(m)=phi(1)
        fa = (m!=a) and solve(nE,sols,neq(copy[m],copy[a]),keep) is None  # forced = phi(a)
        if m==a: fa=True
        if f1: A.append(m)
        elif fa: B.append(m)
        else: free.append(m)
    sep = solve(nE,sols,lambda v:[[ -v(copy[1],c),-v(copy[a],c)] for c in range(3)] and [[v(copy[1],c),-v(copy[a],c)] for c in []] ,keep)
    print(f"L={L}: =phi(1) {len(A)}  =phi(a): {B}  free: {free}",flush=True)

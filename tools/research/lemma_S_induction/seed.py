from math import gcd
from lemS import *
def test(a,b):
    R2=b*b+b+1; T=R2+2*a
    elems,copy,chain,sols=build(a,b,T); nE=len(elems); allk=set(range(nE))
    pat=lambda m: 0 if (m%a==0 and m//a<=b) else (1 if m<=b*b+b else 2)
    full=range(1,b*b+b+1)
    def forced_given(fixset):
        def f(v):
            out=[[v(copy[m],pat(m))] for m in fixset]+[[v(copy[1],1)],[v(copy[a],0)]]
            out.append([-v(copy[m],pat(m)) for m in full if m not in fixset])
            return out
        return solve(nE,sols,f,allk) is None
    Q=[a*u for u in range(1,b+1)]
    out={}
    out['only phi(1),phi(a)']=forced_given([])
    out['Q (a*u, u<=b)']=forced_given(Q)
    out['non-multiples <= 4b']=forced_given([m for m in range(1,4*b+1) if m%a])
    out['[1,2b]']=forced_given(list(range(1,2*b+1)))
    out['[1,ab]']=forced_given(list(range(1,a*b+1)))
    print((a,b),out,flush=True)
for a,b in [(3,5),(4,7),(3,7),(5,8),(4,9)]: test(a,b)

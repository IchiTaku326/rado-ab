from math import gcd
from lemS import *
res=[]
for b in range(3,16):
    for a in range(2,b):
        if gcd(a,b)!=1 or a*a+(b-1)*a>b*b+b+1: continue
        R2=b*b+b+1; T=R2+2*a; K0=max(a*b+4*a,4*b)
        if K0>=b*b+b: res.append((a,b,'K0>=b(b+1)')); continue
        elems,copy,chain,sols=build(a,b,T); nE=len(elems)
        pat=lambda m: 0 if (m%a==0 and m//a<=b) else 1
        def f(v):
            out=[[v(copy[m],pat(m))] for m in range(1,K0+1)]
            out.append([-v(copy[m],pat(m)) for m in range(K0+1,b*b+b+1)])
            return out
        r=solve(nE,sols,f,set(range(nE)))
        res.append((a,b,'OK' if r is None else 'COUNTEREXAMPLE'))
print(res)

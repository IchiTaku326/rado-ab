import sys
from lemS import *
a,b=int(sys.argv[1]),int(sys.argv[2]); R2=b*b+b+1; T=R2+2*a
elems,copy,chain,sols=build(a,b,T); nE=len(elems)
pat=lambda m: 0 if (m%a==0 and m//a<=b) else (1 if m<=b*b+b else 2)
allk=set(range(nE))
# (1) is phi(1)=phi(a) possible?
same=lambda v:[[-v(copy[1],c),v(copy[a],c)] for c in range(3)]
print("phi(1)=phi(a) possible with full chain:", solve(nE,sols,same,allk) is not None)
# (2) per step: minimal chain length so that phi(K+1) is forced (given pattern on [1,K])
def forced(K,L):
    keep={copy[m] for m in range(1,R2+1)}|{chain[t] for t in range(L)}
    want=pat(K+1)
    for c in range(3):
        if c==want: continue
        f=lambda v,c=c:[[v(copy[m],pat(m))] for m in range(1,K+1)]+[[v(copy[K+1],c)]]
        if solve(nE,sols,f,keep) is not None: return False
    return True
row=[]
for K in range(a,R2-1):
    lo,hi=0,T
    while lo<hi:
        mid=(lo+hi)//2
        if forced(K,mid): hi=mid
        else: lo=mid+1
    row.append((K+1,lo))
print("(m=K+1, chain length needed):",row)
print("max needed:",max(r[1] for r in row),"T=",T)

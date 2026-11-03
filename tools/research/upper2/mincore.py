import sys
from red import Nab
from chainfix import chain
def minimize(a,b,n):
    st,T,r,_=chain(a,b,n)
    P=list(range(T+1)); assert st=="UNSAT"
    i=0
    while i<len(P):
        Q=P[:i]+P[i+1:]
        if chain(a,b,n,Q)[0]=="UNSAT": P=Q
        else: i+=1
    return T,r,P
for a,b in [(4,5),(5,6),(6,7),(7,10),(8,11),(9,13),(10,13)]:
    N=Nab(a,b); T,r,P=minimize(a,b,N)
    R2=b*b+b+1
    print((a,b),'T',T,'R2',R2,'T-R2',T-R2,'r',r,'core',P,'| core-R2:',[p-R2 for p in P if p>=R2-5],[ (p, 'S' if (r+b*p)%a==0 else '') for p in P],flush=True)

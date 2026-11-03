# exact check of condition (I2) at each step of the recursive template (no colouring check needed: the lemma proves goodness)
import numpy as np, sys
from math import gcd
def Ls(a,b,K):
    L={2:b*b+b+1}
    for k in range(3,K+1): L[k]=b*(L[k-1]+2*a)+1
    return L
def colsets(a,b,K):
    """colour-0 and colour-1 boolean arrays of T_k on [1,L_k-1] (index = number)"""
    L=Ls(a,b,K); n=L[2]-1
    c0=np.zeros(n+1,bool); c1=np.zeros(n+1,bool)
    for m in range(1,n+1):
        if m%a==0 and m//a<=b: c1[m]=True
        else: c0[m]=True
    out={2:(c0,c1)}
    for k in range(3,K+1):
        Lp=L[k-1]; M=b*(Lp+a); n=L[k]-1
        p0,p1=out[k-1]
        x=np.arange(n+1)
        n0=np.zeros(n+1,bool); n1=np.zeros(n+1,bool)
        nonmult=(x%a!=0)
        n0[(nonmult)&(x<=a*b-1)]=True
        n0[M+1:]=True
        # copy: x=a*m, m<=Lp-1 : colour sigma(C'(m)); sigma swaps 0,1
        ms=np.arange(1,Lp)
        n0[a*ms[p1[1:Lp]]]=True   # C'=1 -> 0
        n1[a*ms[p0[1:Lp]]]=True   # C'=0 -> 1
        n0[0]=False
        out[k]=(n0,n1)
    return out,L
def I2(a,b,K):
    out,L=colsets(a,b,K); res={}
    for k in range(3,K+1):
        Lp=L[k-1]; M=b*(Lp+a); n=b*(Lp+2*a)
        c1=out[k-1][1]; S=np.nonzero(c1)[0]
        # exists m,s in S with M < a m + b s <= n ?
        ok=True
        Sset=np.zeros(len(c1),bool); Sset[S]=True
        for s in S:
            lo=(M-b*s)//a+1; hi=(n-b*s)//a
            lo=max(lo,1); hi=min(hi,len(c1)-1)
            if lo<=hi and Sset[lo:hi+1].any(): ok=False; break
        res[k]=ok
    return res
if __name__=="__main__":
    K=int(sys.argv[1]); B=int(sys.argv[2])
    rows=[]
    for b in range(3,B+1):
        for a in range(2,b):
            if gcd(a,b)!=1: continue
            f1=a*a+(b-1)*a<=b*b+b+1; g=a*a+a*b<=b*b
            r=I2(a,b,K); rows.append((a,b,f1,g,r))
    for k in range(3,K+1):
        f1ok=sum(1 for r in rows if r[2] and r[4][k]); f1n=sum(1 for r in rows if r[2])
        bad=[(r[0],r[1]) for r in rows if r[2] and not r[4][k]]
        print(f'k={k}: f1 cells {f1n}, I2 holds {f1ok}; fails at {bad[:30]}')
    full=[(r[0],r[1]) for r in rows if all(r[4].values())]
    nonf1_ok=[(r[0],r[1]) for r in rows if not r[2] and all(r[4].values())]
    print('I2 holds for all k<=K:',len(full),' of which outside f1:',nonf1_ok[:10])
    gap=[(r[0],r[1]) for r in rows if r[2] and not r[3] and all(r[4].values())]
    print('between golden and f1, I2 holds all k<=K:',len(gap),'e.g.',gap[:15])

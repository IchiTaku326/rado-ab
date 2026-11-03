import numpy as np
from math import gcd
def build(a,b,K):
    L=b*b+b+1; col=np.zeros(L,dtype=np.int8)  # index x (1..L-1)
    for u in range(1,b+1): col[a*u]=1
    Ls=[L]
    for k in range(3,K+1):
        M=b*(L+a); new=np.zeros(M+1,dtype=np.int8)
        x=np.arange(M+1)
        nm=(x%a!=0)
        new[nm & (x<=a*b-1)]=0; new[nm & (x>a*b)]=k-1
        m=x//a
        mul=(~nm)&(x>0)
        cp=mul&(m<=L-1)
        c=col[m[cp]]; c=np.where(c==0,1,np.where(c==1,0,c))
        new[cp]=c
        new[mul&(m>=L)]=k-1
        col=new; L=M+1; Ls.append(L)
    return col,Ls
def check(a,b,col):
    n=len(col)-1
    for z in range(a,n+1,a):
        d=b*z//a
        if d>=n: break
        y=np.arange(1,n-d+1)
        if np.any((col[y]==col[y+d])&(col[y]==col[z])): return False
    return True
bad=[]
for b in range(3,13):
  for a in range(2,b):
    if gcd(a,b)!=1: continue
    for K in (3,4):
        col,Ls=build(a,b,K)
        if len(col)>3_000_000: continue
        if not check(a,b,col): bad.append((a,b,K))
print('bad',bad)
print('example (5,7):',build(5,7,4)[1],' (4,5):',build(4,5,4)[1])

import math, numpy as np, sys
def col(b,j,h,E,n):
    a=b-j; x=np.arange(n+1); v=np.zeros(n+1,int); t=x.copy(); t[0]=1
    for _ in range(6):
        m=(t%a==0); v[m]+=1; t[m]//=a
    c=np.full(n+1,2,np.int8)
    m0=(v==0); c[m0&((x<=a*b-1)|(x>=n-E*b))]=0
    m1=(v==1); c[m1&(x//a<=b*(b+1))]=1
    m2=(v>=2); q=x//(a*a); c[m2&(q<=b)]=0; c[m2&(q>b)&(q<=b+h)]=1
    return a,c
def bad(a,b,n,c):
    s=1;tot=0
    while b*s<=n-1 and a*s<=n:
        d=b*s;z=a*s;y=np.arange(1,n-d+1); tot+=int(((c[y]==c[y+d])&(c[y]==c[z])).sum()); s+=1
    return tot
j=3
for b in range(23,80):
    a=b-j
    if math.gcd(a,b)!=1: continue
    N=b**3+2*b*b; n=N-45-a-1 if b>=43 else N-46
    a,c=col(b,j,4,2,n); print(b, 'n=N-45-a-1' if b>=43 else 'n=N-46', bad(a,b,n,c), flush=True)

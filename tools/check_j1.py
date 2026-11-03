import math, numpy as np, sys
def col(b,a,n,E,H):
    x=np.arange(n+1); v=np.zeros(n+1,int); t=x.copy(); t[0]=1
    for _ in range(8):
        m=(t%a==0); v[m]+=1; t[m]//=a
    c=np.full(n+1,2,np.int8)
    m0=(v==0); c[m0&((x<=a*b-1)|(x>=n-E))]=0
    m1=(v==1); c[m1&(x//a<=b*(b+1))]=1
    q=x//(a*a); m2=(v>=2); c[m2&(q<=b)]=0; c[m2&(q>b)&(q<=b+H)]=1
    return c
def bad(a,b,n,c):
    s=1;tot=0;first=None
    while b*s<=n-1 and a*s<=n:
        d=b*s;z=a*s;y=np.arange(1,n-d+1); m=(c[y]==c[y+d])&(c[y]==c[z]); k=int(m.sum())
        if k and first is None: yy=int(y[m][0]); first=(yy,yy+d,z,s)
        tot+=k; s+=1
    return tot,first
if __name__=="__main__":
 for b in map(int,sys.argv[1:]):
    pass
    a=b-1;n=b**3+2*b*b+b-5
    for H in (1,2,3):
        for E in range(0,3*b+1):
            c=col(b,a,n,E,H); t,f=bad(a,b,n,c)
            if t==0: print(b,'H',H,'E',E,'OK'); break
        else: print(b,'H',H,'no E; last',t,f)

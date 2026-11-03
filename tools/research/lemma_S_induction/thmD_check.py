from math import gcd
import numpy as np
def build_T(a,b,K):
    L=b*b+b+1; col=np.zeros(L,dtype=np.int8)  # index x in [1,L-1]
    for u in range(1,b+1): col[a*u]=1
    out={2:(L,col)}; I2={}
    for k in range(3,K+1):
        M=b*(L+a); n=b*(L+2*a)
        C1=np.nonzero(col==1)[0]; C1set=set(C1.tolist())
        ok=True
        for w in range(M+1,n+1):
            for s in C1:
                r=w-b*int(s)
                if r<=0: break
                if r%a==0 and (r//a) in C1set: ok=False; break
            if not ok: break
        I2[k]=ok
        sig=lambda c: 1 if c==0 else (0 if c==1 else c)
        new=np.zeros(n+1,dtype=np.int8)
        for x in range(1,n+1):
            if x%a:
                new[x]=0 if x<=a*b-1 else (k-1 if x<=M else 0)
            else:
                m=x//a
                if m<=L-1: new[x]=sig(int(col[m]))
                elif x<=M: new[x]=k-1
                else: new[x]=0
        L=n+1; col=new; out[k]=(L,col)
        if not ok: break
    return out,I2
def mono(a,b,col):
    n=len(col)-1; bad=0
    for s in range(1,n//b+1):
        z=a*s
        if z>n: break
        c=col[z]; d=b*s
        bad+=int(np.sum((col[1:n-d+1]==c)&(col[1+d:n+1]==c)))
    return bad
res=[];mis=0
for b in range(3,13):
    for a in range(2,b):
        if gcd(a,b)!=1 or a*a+(b-1)*a>b*b+b+1: continue
        D=a*a+a*b-b*b
        pred= None if (D<=1 or a+1<=D<=2*a) else (4 if D>=2*a+1 else 5)
        out,I2=build_T(a,b,5)
        first=next((k for k in sorted(I2) if not I2[k]),None)
        if first==3: first=3
        badT=[k for k,(L,col) in out.items() if I2.get(k,True) and mono(a,b,col)>0]
        if first!=pred: mis+=1; res.append((a,b,D,pred,first))
        if badT: res.append(('NOT GOOD',a,b,badT))
print("Theorem D (first failing k<=5) mismatches:",mis,res)

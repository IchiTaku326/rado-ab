from math import gcd
from red import Nab
def phi(a,b,m):
    if m%a==0 and m//a<=b: return 0
    if m<=b*(b+1): return 1
    if m==b*b+b+1: return 2
def check(a,b):
    N=Nab(a,b); R2=b*b+b+1; r=N%b or b; T=(N-r)//b
    P=[T-R2-a,T-R2,T-a,T]
    if P[0]<0: return 'P1<0'
    spec={}
    for t in range(T+1):
        x=r+b*t
        if x%a==0 and x//a<=R2: spec[t]=phi(a,b,x//a)
    Q1=[q for q,c in spec.items() if c==1 and q not in P and all(1<=abs(q-p)<=b*(b+1) and phi(a,b,abs(q-p))==1 for p in P)]
    def kills(q,p):
        d=abs(q-p); return d>=1 and d<=R2 and phi(a,b,d)==0
    Q0=[q for q,c in spec.items() if c==0 and q not in P and (kills(q,P[0]) or kills(q,P[3])) and (kills(q,P[1]) or kills(q,P[2]))]
    return (bool(Q1) and bool(Q0)), (Q1[:2],Q0[:2])
bad=[];n=0;aM=0
for b in range(4,301):
  for a in range(2,b):
    if gcd(a,b)!=1 or a*a+(b-1)*a<=b*b+b+1: continue
    M=b*(b*b+b+a+1)
    if M%a==0: aM+=1; continue
    n+=1; ok,info=check(a,b)
    if ok is not True: bad.append((a,b,ok,info))
print('cells',n,'a|M skipped',aM,'fail',len(bad),bad[:15])

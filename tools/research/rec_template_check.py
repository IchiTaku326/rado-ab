import numpy as np, sys
from math import gcd
from rec_template import template
def checkv(a,b,C):
    C=np.array([-1]+C[1:],dtype=np.int16); n=len(C)-1; bad=0
    s=1
    while a*s<=n and b*s<n:
        z=a*s; d=b*s; cz=C[z]
        y=C[1:n-d+1]; x=C[1+d:n+1]
        bad+=int(np.count_nonzero((y==cz)&(x==cz))); s+=1
    return bad
if __name__=="__main__":
    K=int(sys.argv[1]); B=int(sys.argv[2]); res=[]
    for b in range(3,B+1):
        for a in range(2,b):
            if gcd(a,b)!=1: continue
            f1 = a*a+(b-1)*a<=b*b+b+1
            C=template(a,b,K); bad=checkv(a,b,C)
            res.append((a,b,f1,len(C),bad))
    ok=[r for r in res if r[2] and r[4]==0]; badf1=[r for r in res if r[2] and r[4]>0]; out=[r for r in res if not r[2]]
    print(f'k={K} b<={B}: f1 cells {len(ok)+len(badf1)}, template valid {len(ok)}, invalid {[(r[0],r[1],r[4]) for r in badf1]}')
    print(' outside f1:',[(r[0],r[1],r[4]) for r in out][:30])

from math import gcd
def cls(a,b):
    D=a*a+a*b-b*b
    if not (a*a+(b-1)*a<=b*b+b+1): return None
    if D<=1 or a+1<=D<=2*a: return 'all'
    return 'k4' if D>=2*a+1 else 'k5'
# find orbit starts: pairs whose preimage (2a-b, b-a) is not a valid pair with 1<=a'<b'
viol=0; orbits=0
for b in range(2,3000):
    for a in range(1,b):
        if gcd(a,b)!=1: continue
        pa,pb=2*a-b,b-a
        if 1<=pa<pb: continue
        D=a*a+a*b-b*b
        if D<2: continue
        seq=[];x,y=a,b
        while y<200000:
            c=cls(x,y)
            if c: seq.append(c)
            x,y=x+y,x+2*y
        if not seq: continue
        orbits+=1
        if seq.count('all')>1 or seq.count('k4')>1: viol+=1
        if 'k5' in seq and any(s!='k5' for s in seq[seq.index('k5'):]): viol+=1
print("orbits checked",orbits,"violations",viol)
# delta>0 fraction vs (1-rho)/rho^2
from math import ceil
def sigma(x,a,b):
    best=-1
    for j in range(0,int(x//b)+2):
        r=x-b*j
        if r<=0: break
        i=ceil(r/a)-1
        if i>=0: best=max(best,a*i+b*j)
    return best
bins={}
for b in range(3,241):
    for a in range(2,b):
        if gcd(a,b)!=1: continue
        D=a*a+a*b-b*b;E=D-a-b-1
        if E<=0: continue
        x=b*E/a; d=(ceil(x)-1)-sigma(x,a,b)
        r=round(a/b/0.04)*0.04
        bins.setdefault(r,[0,0]); bins[r][0]+=1; bins[r][1]+=(d>0)
for r in sorted(bins):
    if 0.64<r<0.96: print(f"a/b~{r:.2f}: observed {bins[r][1]/bins[r][0]:.2f}  predicted {(1-r)/r/r:.2f}  (n={bins[r][0]})")

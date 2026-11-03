from math import gcd, sqrt
phi=(1+sqrt(5))/2
def sigma(a,b,E):
    # max a*i+b*j with a*(a*i+b*j) < b*E, 0<=i,j<=b-1
    best=-1
    for i in range(0,b):
        r=b*E - a*a*i   # need a*b*j < r  -> j <= (r-1)//(a*b)
        if r<=0: break
        j=min(b-1,(r-1)//(a*b))
        best=max(best,a*i+b*j)
    return best
rows=[]
for b in range(3,241):
  for a in range(2,b):
    if gcd(a,b)!=1: continue
    D=a*a+a*b-b*b; E=D-a-b-1
    if E<=0: continue
    R2=b*b+b+1; M=b*(R2+a)
    sig=sigma(a,b,E); N=a*(b*(a+b)-sig)
    uni=a*(-(-(M+1)//a))
    t=a-b/phi; x=b*E/a; F=a*b-a-b
    cat='plateau' if N==a*b*(a+b) else ('unified' if N==uni else 'stair')
    rows.append((cat,t,a/b,x,F,a,b))
for c in ['plateau','stair','unified']:
    r=[x for x in rows if x[0]==c]
    print(c,len(r),'t',round(min(x[1] for x in r),3),round(max(x[1] for x in r),3),'a/b',round(min(x[2] for x in r),3),round(max(x[2] for x in r),3))
print('plateau iff x<=a:', all((x[0]=='plateau')==(x[3]<=x[5]) for x in rows))
print('x>F => unified:', sum(1 for x in rows if x[3]>x[4] and x[0]!='unified'),'/',sum(1 for x in rows if x[3]>x[4]))
print('unified but x<=F:', sum(1 for x in rows if x[3]<=x[4] and x[0]=='unified'))
print('pred plateau t-width 1/(phi^2 sqrt5)=',1/(phi**2*sqrt(5)),' t0=',phi/sqrt(5),' ratio for x=F ~',1/phi+1/(phi**2*sqrt(5)))
# x vs approx phi*sqrt5*b*(t-t0)
import statistics
err=[abs(x[3]-phi*sqrt(5)*x[6]*(x[1]-phi/sqrt(5)))/x[6] for x in rows]
print('max |x - phi sqrt5 b (t-t0)|/b =',round(max(err),3))
# bins of rho = a/b : observed fraction of 'stair' vs predicted 1-g(rho), g = 1+1/rho-1/rho^2
import collections
bins=collections.defaultdict(lambda:[0,0])
for c,t,rho,x,F,a,b in rows:
    if c=='plateau': continue
    k=round(rho,2)//0.04*0.04
    bins[round(k,2)][0]+= (c=='stair'); bins[round(k,2)][1]+=1
for k in sorted(bins):
    rho=k+0.02; g=1+1/rho-1/rho**2
    s,n=bins[k]; print(f"a/b~{rho:.2f}: stair {s}/{n} = {s/n:.2f}   predicted 1-g = {1-g:.2f}")

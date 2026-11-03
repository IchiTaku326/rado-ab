from math import gcd, ceil, sqrt
phi=(1+sqrt(5))/2
def Nab(a,b):
    M=b*(b*b+b+a+1); A=sorted({a*u2+b*u for u in range(1,b+1) for u2 in range(1,b+1)})
    mp=min([m for m in A if a*m>M],default=None)
    return min(a*mp if mp else 10**18, M+a*b+1), M
def sigma(x,a,b):  # max ai+bj < x
    best=-1
    for j in range(0,int(x//b)+2):
        r=x-b*j
        if r<=0: break
        i=ceil(r/a)-1
        if i>=0: best=max(best,a*i+b*j)
    return best
bad1=bad2=bad3=0; cnt=0; plateau_bad=0
for b in range(3,151):
    for a in range(2,b):
        if gcd(a,b)!=1: continue
        cnt+=1
        N,M=Nab(a,b); D=a*a+a*b-b*b; E=D-(a+b+1)
        main=(a*a+(b-1)*a<=b*b+b+1)
        if main!=(E<=0): bad1+=1
        if E<=0:
            if N!=b*(b*b+b+2*a+1)+1: bad2+=1
        else:
            x=b*E/a
            f=min(M+a*b+1, a*(b*(a+b)-sigma(x,a,b)))
            if f!=N: bad2+=1
            # staircase: N = a*ceil((M+1)/a) + a*delta, delta=(ceil(x)-1)-sigma(x)
            dlt=(ceil(x)-1)-sigma(x,a,b)
            if a*((M+1+a-1)//a)+a*dlt!=N: bad3+=1
            if (N==a*b*(a+b))!=(0<x<=a): plateau_bad+=1
print("pairs",cnt,"| main<->E<=0 mismatches",bad1,"| Prop NinD mismatches",bad2,"| staircase mismatches",bad3,"| plateau N=ab(a+b) <-> 0<x<=a mismatches",plateau_bad)

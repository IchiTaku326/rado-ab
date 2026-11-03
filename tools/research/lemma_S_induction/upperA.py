from math import gcd, ceil
def info(a,b):
    A={a*u2+b*u for u in range(1,b+1) for u2 in range(1,b+1)}
    top=b*b+b
    mW=4*b+ceil((2*b+1)/a)+1
    P1=[m for m in range(1,top+1) if not (m%a==0 and m//a<=b)]
    nonA=[m for m in P1 if m not in A]
    return mW,[m for m in nonA if m>=mW], max(nonA) if nonA else 0
bad=0
for b in range(4,60):
    for a in range(3,b):
        if gcd(a,b)!=1 or a*a+(b-1)*a>b*b+b+1: continue
        mW,up,mx=info(a,b)
        if up: bad+=1; 
        if up and b<16: print((a,b),"mW",mW,"nonA above mW:",up[:12],"max nonA",mx)
print("cells with nonA above mW:",bad)

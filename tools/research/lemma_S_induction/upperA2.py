from math import gcd
worst=[]
for b in range(4,200):
    for a in range(2,b):
        if gcd(a,b)!=1 or a*a+(b-1)*a>b*b+b+1: continue
        A=set(a*u2+b*u for u in range(1,b+1) for u2 in range(1,b+1))
        nonA=[m for m in range(1,b*b+b+1) if not (m%a==0 and m//a<=b) and m not in A]
        mx=max(nonA); worst.append((mx-a*b,a,b,mx))
worst.sort()
print("max(nonA)-ab  min/max:",worst[0],worst[-1])
print("cells with max nonA > ab:",[w for w in worst if w[0]>0][:10])

import sys
def N3(a,b):
    M=b*(b*b+b+a+1); A={a*up+b*u for u in range(1,b+1) for up in range(1,b+1)}
    return min([a*m for m in A if a*m>M]+[M+a*b+1])
def T2(a,b):
    n=b*(b+1); return n,[None]+[1 if (m%a==0 and m//a<=b) else 0 for m in range(1,n+1)]
def step(a,b,prev,n,k):
    """k-colour template on [1,n] from the (k-1)-colour template prev on [1,Rprev-1]; M_k = b(Rprev + a)"""
    Rp=len(prev)  # prev has indices 0..Rp-1, Rprev = Rp
    M=b*(Rp+a)
    sig=lambda c: 1 if c==0 else (0 if c==1 else c)
    C=[None]*(n+1)
    for x in range(1,n+1):
        if x>M: C[x]=0
        elif x%a:
            C[x]=0 if x<=a*b-1 else k-1
        else:
            m=x//a
            C[x]=sig(prev[m]) if m<=Rp-1 else k-1
    return C
def check(a,b,C):
    n=len(C)-1; bad=0
    for s in range(1,n//a+1):
        z=a*s; d=b*s
        if d>=n: break
        cz=C[z]
        for y in range(1,n-d+1):
            if C[y]==cz and C[y+d]==cz: bad+=1
    return bad
def template(a,b,k,R3=None):
    n2,C=T2(a,b)
    # 3 colours: n = N3-1 (general theorem template); built by step but T block = [M+1, N-1]
    R=N3(a,b) if R3 is None else R3
    C=step(a,b,C,R-1,3)
    for kk in range(4,k+1):
        Rp=len(C); n=b*(Rp+2*a)
        C=step(a,b,C,n,kk); R=n+1
    return C
if __name__=="__main__":
    for a,b,k in [(3,4,3),(3,4,4),(4,5,4),(2,5,4),(3,5,4),(3,4,5),(5,7,4),(4,7,4),(5,8,4),(7,9,4),(3,5,5),(2,3,4)]:
        C=template(a,b,k); n=len(C)-1
        print((a,b),'k',k,'n',n,'-> lower bound',n+1,'mono',check(a,b,C),flush=True)

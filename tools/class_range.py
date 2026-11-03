import io, contextlib
from sub import test
def uns(a,b,n,K,P1,P2):
    buf=io.StringIO()
    def inS(x):
        if x%a==0 and x<=a*K: return True
        if (n-x)%b==0:
            p=(n-x)//b; return P1<=p<=P2
        return False
    with contextlib.redirect_stdout(buf): test(a,b,n,inS,'')
    return 'UNSAT' in buf.getvalue()
for a,b,n in [(8,13,2588),(12,13,2544),(15,17,5475),(20,23,13180),(21,23,13209),(22,25,16830)]:
    K=b*b+b+1; L=(n-1)//b
    # minimal top range [0,P2]
    lo,hi=0,L
    while lo<hi:
        m=(lo+hi)//2
        if uns(a,b,n,K,0,m): hi=m
        else: lo=m+1
    P2=lo
    # maximal P1 with [P1,P2]
    lo,hi=0,P2
    while lo<hi:
        m=(lo+hi+1)//2
        if uns(a,b,n,K,m,P2): lo=m
        else: hi=m-1
    print((a,b,n),'class p range needed: [',lo,',',P2,'] of [0,',L,']  b^2=',b*b,' K=',K, 'n/b - p2=',L-P2, flush=True)

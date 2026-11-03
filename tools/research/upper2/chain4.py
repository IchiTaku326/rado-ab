import subprocess, os, sys
CAD=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","..","bin_linux","cadical")
def template(a,b,k):
    L={2:b*b+b+1}
    for j in range(3,k+1): L[j]=b*(L[j-1]+2*a)+1
    T={x:(1 if x%a==0 and x//a<=b else 0) for x in range(1,L[2])}
    for j in range(3,k+1):
        Lp=L[j-1]; M=b*(Lp+a); n=b*(Lp+2*a); C={}
        for x in range(1,n+1):
            if x%a:
                C[x]=0 if x<=a*b-1 else (j-1 if x<=M else 0)
            else:
                m=x//a
                if m<=Lp-1: c=T[m]; C[x]={0:1,1:0}.get(c,c)
                elif x<=M: C[x]=j-1
                else: C[x]=0
        T=C
    return T,L
def chainprob(a,b,k,n,timeout=300,free_mult=False):
    T,L=template(a,b,k)
    col=lambda x: T.get(x,0)        # multiples of a above template range: colour 0 (top block)
    r=n%b or b; P=list(range(r,n+1,b)); idx={x:i for i,x in enumerate(P)}
    v=lambda x,c:k*idx[x]+c+1
    cl=[[v(x,c) for c in range(k)] for x in P]
    for x in P:
        for c in range(k):
            for d in range(c+1,k): cl.append([-v(x,c),-v(x,d)])
        if x%a==0 and not free_mult: cl.append([v(x,col(x))])
    for i,y in enumerate(P):
        for x in P[i+1:]:
            if (a*(x-y))%b: continue
            z=a*(x-y)//b
            if z<1 or z>n: continue
            if z in idx:
                for c in range(k): cl.append([-v(x,c),-v(y,c),-v(z,c)])
            else:
                c=col(z); cl.append([-v(x,c),-v(y,c)])
    f=f"/tmp/c4_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {k*len(P)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    try: out=subprocess.run([CAD,"-q",f],capture_output=True,text=True,timeout=timeout).stdout
    except subprocess.TimeoutExpired: return "TIMEOUT"
    return "UNSAT" if "UNSAT" in out else "SAT"
if __name__=="__main__":
    k=int(sys.argv[1])
    for a,b in [(3,4),(3,5),(2,5),(4,7),(5,8),(3,7),(2,7),(4,9),(4,5),(5,7)]:
        T,L=template(a,b,k)
        print((a,b),'k',k,'L',L[k],chainprob(a,b,k,L[k]),chainprob(a,b,k,L[k]-1),flush=True)

import subprocess, os, sys
from math import gcd
CAD=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","..","bin_linux","cadical")
def Nab(a,b):
    M=b*(b*b+b+a+1); A=sorted({a*u2+b*u for u in range(1,b+1) for u2 in range(1,b+1)})
    mp=[m for m in A if a*m>M]
    return min(a*mp[0] if mp else 10**18, M+a*b+1)
def solve(a,b,n,K,types,extra=(),timeout=300):
    """elements: copy a*[1,K] (<=n), chain {x<=n: x = n mod b}, extra numbers. types: subset of
    'copy' (all solutions inside copy), 'cc' (x,y chain, z copy), 'all' (every solution among the elements)"""
    E=set(a*m for m in range(1,K+1) if a*m<=n)|set(range(n%b or b,n+1,b))|set(e for e in extra if e<=n)
    E=sorted(E); idx={x:i for i,x in enumerate(E)}; v=lambda x,c:3*idx[x]+c+1
    cl=[[v(x,0),v(x,1),v(x,2)] for x in E]+[[v(E[0],0)]]
    Es=set(E); ch=set(range(n%b or b,n+1,b)); cp=set(a*m for m in range(1,K+1))
    tri=0
    for z in E:
        if z%a: continue
        d=b*z//a
        for y in E:
            x=y+d
            if x>n: break
            if x not in Es: continue
            ok=('all' in types) or ('copy' in types and x in cp and y in cp and z in cp) or ('cc' in types and x in ch and y in ch and z in cp) \
               or ('cross' in types and z in cp and ((x in ch) != (y in ch)))
            if ok:
                tri+=1; T=sorted({x,y,z})
                for c in range(3): cl.append([-v(t,c) for t in T])
    f=f"/tmp/r_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {3*len(E)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    try: out=subprocess.run([CAD,"-q",f],capture_output=True,text=True,timeout=timeout).stdout
    except subprocess.TimeoutExpired: return "TIMEOUT"
    return "UNSAT" if "UNSAT" in out else "SAT"
if __name__=="__main__":
    cells=[(4,5),(5,6),(6,7),(7,9),(7,10),(8,11),(9,13),(5,7),(3,4)]
    for a,b in cells:
        N=Nab(a,b); R2=b*b+b+1; f1=a*a+(b-1)*a<=b*b+b+1
        res=[]
        for n in (N,N-1):
            res.append((n,solve(a,b,n,R2,{'all'},timeout=120),solve(a,b,n,R2,{'copy','cc'},timeout=120)))
        print((a,b),'f1' if f1 else 'OUT','N=',N,res,flush=True)

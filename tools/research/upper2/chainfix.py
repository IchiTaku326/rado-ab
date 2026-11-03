import subprocess, os, sys
from red import Nab, CAD
def phi(a,b,m):
    R2=b*b+b+1
    if m%a==0 and m//a<=b: return 0
    if m<=b*(b+1): return 1
    if m==R2: return 2
    return None
def chain(a,b,n,positions=None,timeout=120,fix_special=True):
    r=n%b or b; T=(n-r)//b; R2=b*b+b+1
    P=list(range(T+1)) if positions is None else sorted(positions)
    v=lambda t,c:3*P.index(t)+c+1
    cl=[[v(t,0),v(t,1),v(t,2)] for t in P]
    for c in range(3):
        for t in P:
            for d in range(c+1,3): cl.append([-v(t,c),-v(t,d)])
    spec=[]
    for t in P:
        x=r+b*t
        if fix_special and x%a==0 and x//a<=R2:
            cl.append([v(t,phi(a,b,x//a))]); spec.append(t)
    for i,t in enumerate(P):
        for u in P[i+1:]:
            s=u-t
            if s<=R2:
                c=phi(a,b,s)
                cl.append([-v(t,c),-v(u,c)])
    f=f"/tmp/c_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {3*len(P)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    out=subprocess.run([CAD,"-q",f],capture_output=True,text=True,timeout=timeout).stdout
    return ("UNSAT" if "UNSAT" in out else "SAT"), T, r, spec
if __name__=="__main__":
    for a,b in [(4,5),(5,6),(6,7),(7,9),(7,10),(8,11),(9,13),(10,13),(11,14),(3,4),(5,7)]:
        N=Nab(a,b)
        print((a,b),'N',N,[ (n,)+chain(a,b,n)[:3]+(chain(a,b,n)[3][:12],) for n in (N,N-1)],flush=True)

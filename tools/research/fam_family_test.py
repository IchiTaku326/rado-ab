import subprocess, sys, os, itertools
CAD="/home/claude/t/shim/cadical"
from math import gcd
def Nf1(a,b): return b*(b*b+b+2*a+1)+1
def fam(a,b,Q,S,R,hiQ=None):
    n=Nf1(a,b); K=b*b+b+1; hiQ=Q if hiQ is None else hiQ
    qs=set(range(0,Q+1))|set(range(max(0,b-hiQ),b+4))
    E=set([a])
    for q in qs:
        for s in range(-S,S+1):
            for r in range(-R,R+1):
                p=q*b+s*a+r
                if p>=0 and n-b*p>=1: E.add(n-b*p)
                m=q*b+s*a+r
                if 1<=m<=K: E.add(a*m)
    return sorted(E),n
def solve(a,b,E,n):
    idx={x:i for i,x in enumerate(E)}; v=lambda x,c:3*idx[x]+c+1; Es=set(E)
    cl=[[v(x,0),v(x,1),v(x,2)] for x in E]+[[v(a,0)]]
    for z in E:
        if z%a: continue
        d=b*(z//a)
        for y in E:
            if y+d>n: break
            if y+d in Es:
                T=sorted({y,y+d,z}); cl+=[[-v(t,c) for t in T] for c in range(3)]
    f=f"/tmp/f_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {3*len(E)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    out=subprocess.run([CAD,"-q",f],capture_output=True,text=True).stdout
    return len(cl),"UNSAT" if "s UNSAT" in out else "SAT"
if __name__=="__main__":
    Q,S,R=map(int,sys.argv[1:4]); cells=[tuple(map(int,c.split(','))) for c in sys.argv[4:]]
    for a,b in cells:
        E,n=fam(a,b,Q,S,R); print((a,b),'f1' if a*a+(b-1)*a<=b*b+b+1 else 'OUT', len(E),*solve(a,b,E,n),flush=True)

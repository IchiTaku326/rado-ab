import subprocess, os, sys
sys.path.insert(0,'/home/claude/up')
from core3 import build
CAD="/home/claude/t/shim/cadical"
def check(a,b):
    R2=b*b+b+1; T=R2+2*a-1
    S=sorted(set(a*m for m in range(1,R2+1))|set(1+b*t for t in range(T+1)))
    S2,cl=build(a,b,S); idx={x:i for i,x in enumerate(S2)}; v=lambda x,c:3*idx[x]+c+1
    bad=[]
    for s in range(1,R2):
        extra=[]
        # phi(s)==phi(R2): OR_c (v(as,c) & v(aR2,c)) -> for 3 colours encode with aux: simpler: forbid differing colours pairwise
        for c in range(3):
            for d in range(3):
                if c!=d: extra.append([-v(a*s,c),-v(a*R2,d)])
        cl2=cl+extra
        f=f"/tmp/s2_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {3*len(S2)} {len(cl2)}\n"+"".join(" ".join(map(str,x))+" 0\n" for x in cl2))
        if "s SAT" in subprocess.run([CAD,"-q",f],capture_output=True,text=True).stdout: bad.append(s)
    return bad
for a,b in [(3,4),(3,5),(4,7),(3,7)]:
    print((a,b),'s<R2 with phi(s)=phi(R2) possible:',check(a,b),flush=True)

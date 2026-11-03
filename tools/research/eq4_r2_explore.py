import subprocess, sys, os
from math import gcd
CAD="/home/claude/t/shim/cadical"
def colourable(a,b,n,k=2):
    v=lambda x,c:k*(x-1)+c+1
    cl=[[v(x,c) for c in range(k)] for x in range(1,n+1)]
    if k>2:
        for x in range(1,n+1):
            for c in range(k):
                for d in range(c+1,k): cl.append([-v(x,c),-v(x,d)])
    cl.append([v(1,0)])
    seen=set()
    for z in range(a,n+1,a):
        s=z//a; t=b*s
        for w in range(1,n+1):
            for y in range(1,n+1):
                x=t+w-y
                if x<1: break
                if x>n: continue
                T=tuple(sorted({x,y,w,z}))
                if T in seen: continue
                seen.add(T)
                for c in range(k): cl.append([-v(q,c) for q in T])
    f=f"/tmp/e4_{os.getpid()}.cnf"; open(f,'w').write(f"p cnf {k*n} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    out=subprocess.run([CAD,"-q","-t","20",f],capture_output=True,text=True).stdout
    return "UNSAT" not in out
def R(a,b,k=2,lim=200):
    n=1
    while n<lim and colourable(a,b,n,k): n+=1
    return n
for b in range(2,9):
    print(b,[ (a,R(a,b)) for a in range(1,b+4) if gcd(a,b)==1],flush=True)

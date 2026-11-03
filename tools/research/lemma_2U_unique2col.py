import subprocess, os
from math import gcd
CAD="/home/claude/t/shim/cadical"
def unique(a,b,n=None):
    n=b*(b+1) if n is None else n
    cl=[[1]]  # var x: True = colour 1? use: var x true -> colour B ; colour of 1 = A (false)
    cl=[[-1]]
    for s in range(1,n+1):
        z=a*s; d=b*s
        if z>n: break
        for y in range(1,n-d+1):
            T=sorted({y,y+d,z}); cl.append([t for t in T]); cl.append([-t for t in T])
    tm=[(m%a==0 and m//a<=b) for m in range(1,n+1)]
    base=list(cl)
    cl.append([(-(m) if tm[m-1] else m) for m in range(1,n+1)])  # not equal to template
    def solve(c):
        f=f"/tmp/two_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {n} {len(c)}\n"+"".join(" ".join(map(str,x))+" 0\n" for x in c))
        return "s SAT" in subprocess.run([CAD,"-q",f],capture_output=True,text=True).stdout
    return solve(base), solve(cl)
if __name__=="__main__":
    bad=[];cnt=0
    for b in range(3,41):
        for a in range(2,b):
            if gcd(a,b)!=1: continue
            cnt+=1; ok,other=unique(a,b)
            if not ok or other: bad.append((a,b,ok,other))
    print('cells b<=40:',cnt,'exceptions (template not good / another colouring exists):',bad)

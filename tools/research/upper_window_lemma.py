import subprocess, os
CAD="/home/claude/t/shim/cadical"
def phi(a,b,m):
    R2=b*b+b+1
    if m%a==0 and m//a<=b: return 0
    if m<=b*(b+1): return 1
    return 2
def run(a,b,ts,T=None):
    R2=b*b+b+1; T=R2+2*a if T is None else T
    ts=sorted(t for t in ts if 0<=t<=T)
    idx={t:i for i,t in enumerate(ts)}; v=lambda t,c:3*idx[t]+c+1
    cl=[[v(t,0),v(t,1),v(t,2)] for t in ts]
    for t in ts:     # coupling: 1+bt = a m, m<=R2 -> colour fixed phi(m)
        x=1+b*t
        if x%a==0 and x//a<=R2: cl.append([v(t,phi(a,b,x//a))])
    for i,t in enumerate(ts):
        for u in ts[i+1:]:
            s=u-t
            if s<=R2:
                c=phi(a,b,s); cl.append([-v(t,c),-v(u,c)])
    f=f"/tmp/l4_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {3*len(ts)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    out=subprocess.run([CAD,"-q",f],capture_output=True,text=True).stdout
    return "UNSAT" if "UNSAT" in out else "SAT"
if __name__=="__main__":
    for a,b in [(3,4),(3,5),(3,7),(4,7),(5,8),(3,8),(2,9),(4,9),(7,12)]:
        R2=b*b+b+1; T=R2+2*a
        full=run(a,b,range(T+1))
        W=list(range(0,2*a+1))+list(range(R2,R2+2*a+1))
        spec=[t for t in range(T+1) if (1+b*t)%a==0 and (1+b*t)//a<=R2]
        print((a,b),'fixed phi, full chain:',full,'| windows only:',run(a,b,W),'| windows+special:',run(a,b,W+spec),flush=True)

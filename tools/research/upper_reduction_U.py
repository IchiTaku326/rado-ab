import subprocess, os
CAD="/home/claude/t/shim/cadical"
def run(a,b,Dint=True,T=None,K=None,zchain=False):
    R2=b*b+b+1; K=R2 if K is None else K; T=R2+2*a if T is None else T
    num={}
    def nid(x):
        if x not in num: num[x]=len(num)
    for m in range(1,K+1): nid(a*m)
    for t in range(0,T+1): nid(1+b*t)
    v=lambda x,c:3*num[x]+c+1
    cl=[[v(x,0),v(x,1),v(x,2)] for x in num]+[[v(a,0)]]
    if Dint:
        for Z in range(a,K+1,a):
            d=b*Z//a
            for Y in range(1,K+1):
                X=Y+d
                if X>K: break
                T3=sorted({a*X,a*Y,a*Z})
                for c in range(3): cl.append([-v(t,c) for t in T3])
    for t in range(0,T+1):
        for u in range(t+1,T+1):
            s=u-t; z=a*s
            if s<=K or (zchain and z in num):
                T3=sorted({1+b*t,1+b*u,z})
                for c in range(3): cl.append([-v(q,c) for q in T3])
    f=f"/tmp/l3_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {3*len(num)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    out=subprocess.run([CAD,"-q",f],capture_output=True,text=True,timeout=110).stdout
    return "UNSAT" if "UNSAT" in out else "SAT"
if __name__=="__main__":
    for a,b in [(3,4),(3,5),(3,7),(4,7),(5,8),(3,8),(2,9)]:
        print((a,b),'T=R2+2a:',run(a,b),' T-1:',run(a,b,T=b*b+b+1+2*a-1),' noDint:',run(a,b,Dint=False),flush=True)

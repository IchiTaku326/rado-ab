import subprocess, sys, os, itertools
CAD="/home/claude/t/shim/cadical"
def N(a,b):
    M=b*(b*b+b+a+1); A={a*up+b*u for u in range(1,b+1) for up in range(1,b+1)}
    return min([a*m for m in A if a*m>M]+[M+a*b+1])
def family(a,j,Q1,Q2,R):
    b=a+j; n=N(a,b); K=b*b+b+1; r0=n%b
    qs=set(range(0,Q1+1))|set(range(max(0,a-Q2),a+8))
    S=set()
    for q in qs:
        for r in range(-R,R+1):
            p=q*a+r
            if p>=0:
                x=n-b*p
                if 1<=x<=n: S.add(x)
            m=q*b+r
            if 1<=m<=K: S.add(a*m)
    S.add(a)
    return sorted(S),n,b
def solve(a,j,Q1,Q2,R):
    S,n,b=family(a,j,Q1,Q2,R); idx={x:i for i,x in enumerate(S)}; v=lambda x,c:3*idx[x]+c+1
    cl=[[v(x,0),v(x,1),v(x,2)] for x in S]+[[v(a,0)]]
    Sset=set(S)
    for z in S:
        if z%a: continue
        s=z//a; d=b*s
        for y in S:
            if y+d>n: break
            if y+d in Sset:
                T=sorted({y,y+d,z})
                for c in range(3): cl.append([-v(t,c) for t in T])
    f=f"/tmp/p_{os.getpid()}.cnf"
    with open(f,"w") as h:
        h.write(f"p cnf {3*len(S)} {len(cl)}\n"); h.writelines(" ".join(map(str,c))+" 0\n" for c in cl)
    out=subprocess.run([CAD,"-q",f],capture_output=True,text=True,timeout=600).stdout
    return len(S),len(cl),("UNSAT" if "s UNSAT" in out else "SAT" if "s SAT" in out else "?")
if __name__=="__main__":
    j=int(sys.argv[1]); Q1,Q2,R=map(int,sys.argv[2:5]); As=range(int(sys.argv[5]),int(sys.argv[6])+1)
    for a in As:
        print(a, *solve(a,j,Q1,Q2,R), flush=True)

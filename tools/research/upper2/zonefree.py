import subprocess, sys, os
CAD=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","..","bin_linux","cadical")
def run(a,b,k,n,M,zones,tl=100):
    col=lambda x: 0 if x<a*b else (k-1 if x<=M else 0)
    free=lambda x: x%a==0 or any(l<=x<=h for l,h in zones)
    F=[x for x in range(1,n+1) if free(x)]; idx={x:i for i,x in enumerate(F)}; v=lambda x,c:k*idx[x]+c+1
    cl=[[v(x,c) for c in range(k)] for x in F]
    for z in range(a,n+1,a):
        d=b*z//a
        for y in range(1,n-d+1):
            T=[y+d,y,z]; fx=[t for t in T if not free(t)]; fr=sorted({t for t in T if free(t)})
            for c in range(k):
                if any(col(t)!=c for t in fx): continue
                cl.append([-v(t,c) for t in fr])
    f=f"/tmp/zf_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {k*len(F)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    out=subprocess.run([CAD,"-q","-t",str(tl),f],capture_output=True,text=True).stdout
    st=[l for l in out.splitlines() if l.startswith('s ')]
    return (st[0] if st else 'TIMEOUT'), len(F)
if __name__=="__main__":
    a,b,k,n,M,w=map(int,sys.argv[1:7])
    print(a,b,k,n,M,w,run(a,b,k,n,M,[(a*b-w,a*b+w),(M-w,M+w)],tl=int(sys.argv[7]) if len(sys.argv)>7 else 100),flush=True)

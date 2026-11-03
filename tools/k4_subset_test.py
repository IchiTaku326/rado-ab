import subprocess, os, sys
CAD=os.path.expanduser('~/mnt/sat_solver/bin_linux/cadical')
def test(a,b,n,K,k=4,full=False):
    r=n%b
    S=[x for x in range(1,n+1) if full or (x%a==0 and x<=a*K) or x%b==r]
    idx={x:i for i,x in enumerate(S)}; v=lambda x,c: k*idx[x]+c+1
    cl=[[v(x,c) for c in range(k)] for x in S]
    s=1
    while b*s<=n-1 and a*s<=n:
        d=b*s;z=a*s
        if z in idx:
            for y in S:
                if y+d>n: break
                if y+d in idx:
                    T=sorted({y,y+d,z})
                    for c in range(k): cl.append([-v(t,c) for t in T])
        s+=1
    cl.append([v(S[0],0)])
    open('k.cnf','w').write(f"p cnf {k*len(S)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    o=subprocess.run([CAD,'-q','-t','150','k.cnf'],capture_output=True,text=True).stdout
    return ('UNSAT' if 'UNSATIS' in o else ('SAT' if 'SATISFIABLE' in o else 'UNKNOWN')), len(S), len(cl)
# known 4-colour values and 3-colour values
for a,b,R4,R3 in [(2,3,226,61),(4,3,313,73),(3,2,103,31),(5,2,625,125),(5,3,625,125)]:
    print((a,b),'R4',R4,'R3',R3,' S with K=R3:',test(a,b,R4,R3),' K=R3-1:',test(a,b,R4,R3-1),' all multiples:',test(a,b,R4,10**9), flush=True)

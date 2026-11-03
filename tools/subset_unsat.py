import sys, subprocess, os
CAD=os.path.expanduser('~/mnt/sat_solver/bin_linux/cadical')
def test(a,b,n,inS,tag):
    S=[x for x in range(1,n+1) if inS(x)]; idx={x:i+1 for i,x in enumerate(S)}; inset=set(S)
    v=lambda x,c: 3*(idx[x]-1)+c+1
    cl=[[v(x,0),v(x,1),v(x,2)] for x in S]
    s=1
    while b*s<=n-1 and a*s<=n:
        d=b*s;z=a*s
        if z in inset:
            for y in S:
                if y+d>n: break
                if y+d in inset:
                    T=sorted({y,y+d,z})
                    for c in range(3): cl.append([-v(t,c) for t in T])
        s+=1
    if 1 in inset: cl.append([v(1,0)])
    with open('s.cnf','w') as f:
        f.write(f"p cnf {3*len(S)} {len(cl)}\n"); f.writelines(" ".join(map(str,c))+" 0\n" for c in cl)
    r=subprocess.run([CAD,'-q','s.cnf'],capture_output=True,text=True,timeout=170).stdout
    print(tag,'|S|',len(S),'clauses',len(cl),'UNSAT' if 'UNSATIS' in r else 'SAT',flush=True)
if __name__=='__main__':
    a,b=15,17; n=5475
    va=lambda x: (x%a==0)
    test(a,b,n,lambda x: x%a==0 or x<=a*b or x>=n-3*b,'mult+ends')
    test(a,b,n,lambda x: x%a==0 or x<=2*a*b or x>=n-6*b,'mult+wide ends')
    test(a,b,n,lambda x: x%a==0 or x%b==0 or x<=a*b or x>=n-3*b,'mult a,b+ends')

import subprocess, os, sys
CAD=os.path.expanduser('~/mnt/sat_solver/bin_linux/cadical')
def base_cnf(a,b,n,K):
    r=n%b; S=[x for x in range(1,n+1) if (x%a==0 and x<=a*K) or x%b==r]
    idx={x:i for i,x in enumerate(S)}; v=lambda x,c:3*idx[x]+c+1
    cl=[[v(x,0),v(x,1),v(x,2)] for x in S]
    for x in S:
        for c1 in range(3):
            for c2 in range(c1+1,3): cl.append([-v(x,c1),-v(x,c2)])
    s=1
    while b*s<=n-1 and a*s<=n:
        d=b*s;z=a*s
        if z in idx:
            for y in S:
                if y+d>n: break
                if y+d in idx:
                    T=sorted({y,y+d,z})
                    for c in range(3): cl.append([-v(t,c) for t in T])
        s+=1
    return S,v,cl
def sat(cl,nv,extra):
    with open('/tmp/f.cnf','w') as f:
        f.write(f"p cnf {nv} {len(cl)+len(extra)}\n"); f.writelines(" ".join(map(str,c))+" 0\n" for c in cl+extra)
    o=subprocess.run([CAD,'-q','/tmp/f.cnf'],capture_output=True,text=True).stdout
    return 'UNSATISFIABLE' not in o
a,b,R=map(int,sys.argv[1:4]); n=R-1; K=b*b+b+1
S,v,cl=base_cnf(a,b,n,K); nv=3*len(S)
ref=a  # element a*1
fix=[[v(ref,0)]]
same=[];diff=[];free=[]
for m in range(2,K+1):
    x=a*m
    if x>n: break
    can_same=sat(cl,nv,fix+[[v(x,0)]]); can_diff=sat(cl,nv,fix+[[-v(x,0)]])
    (same if not can_diff else diff if not can_same else free).append(m)
print('S',len(S),'n',n,'K',K)
print('forced SAME colour as a*1: count',len(same), same[:60])
print('forced DIFFERENT from a*1: count',len(diff), diff[:60])
print('free: count',len(free), free[:40])

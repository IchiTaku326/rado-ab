import subprocess, os, sys, time, json
CAD="/home/claude/t/shim/cadical"
def system(a,b):
    R2=b*b+b+1; N=b*(R2+2*a)+1; T=(N-1)//b
    els=[('m',m) for m in range(1,R2+1)]+[('t',t) for t in range(T+1)]
    val=lambda e: a*e[1] if e[0]=='m' else 1+b*e[1]
    return R2,N,T,els,val
def build(a,b,keep):
    R2,N,T,els,val=system(a,b)
    nums={}
    for e in keep: nums.setdefault(val(e),[]).append(e)
    num=list(nums); idx={x:i for i,x in enumerate(num)}; v=lambda x,c:3*idx[x]+c+1
    cl=[[v(x,0),v(x,1),v(x,2)] for x in num]
    first=min(num); cl.append([v(first,0)])
    K=set(keep)
    # copy-internal: a(X-Y)=bZ on indices
    ms=sorted(e[1] for e in keep if e[0]=='m'); mset=set(ms)
    for Z in ms:
        if (b*Z)%a: continue
        d=b*Z//a
        for Y in ms:
            X=Y+d
            if X in mset:
                T3=sorted({a*X,a*Y,a*Z})
                for c in range(3): cl.append([-v(t,c) for t in T3])
    ts=sorted(e[1] for e in keep if e[0]=='t')
    for i,t in enumerate(ts):
        for u in ts[i+1:]:
            s=u-t
            if s in mset:
                T3=sorted({1+b*t,1+b*u,a*s})
                for c in range(3): cl.append([-v(q,c) for q in T3])
    return 3*len(num),cl
def unsat(a,b,keep):
    nv,cl=build(a,b,keep)
    f=f"/tmp/fc_{os.getpid()}.cnf"; open(f,'w').write(f"p cnf {nv} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    out=subprocess.run([CAD,"-q",f],capture_output=True,text=True).stdout
    return "UNSAT" in out
def core(a,b):
    R2,N,T,els,val=system(a,b)
    keep=list(els); assert unsat(a,b,keep)
    # chunked deletion
    step=max(1,len(keep)//8)
    while step>=1:
        i=0
        while i<len(keep):
            trial=keep[:i]+keep[i+step:]
            if unsat(a,b,trial): keep=trial
            else: i+=step
        step//=2
    return keep
if __name__=="__main__":
    a,b=int(sys.argv[1]),int(sys.argv[2]); t0=time.time()
    K=core(a,b); R2=b*b+b+1
    json.dump(K,open(f"core_{a}_{b}.json","w"))
    print(a,b,'core',len(K),round(time.time()-t0),'s')
    print('copy m:',sorted(e[1] for e in K if e[0]=='m'))
    print('chain t:',sorted(e[1] for e in K if e[0]=='t'))

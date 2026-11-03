import subprocess, sys, os
sys.path.insert(0,'/home/claude/t/poly'); from poly import N, CAD
from chain import psi
def run(a,b,n,fixmult=True,mode="all"):
    M=b*(b*b+b+a+1); K=b*b+b+1; r=n%b
    S=[x for x in range(1,n+1) if (x%a==0 and x<=a*K) or x%b==r]; idx={x:i for i,x in enumerate(S)}; Ss=set(S)
    v=lambda x,c:3*idx[x]+c+1
    cl=[[v(x,0),v(x,1),v(x,2)] for x in S]
    chain=lambda x: x%b==r
    if fixmult:
        for x in S:
            if x%a==0 and x<=a*K and not chain(x): cl.append([v(x,psi(a,b,x//a,M))])
    for z in S:
        if z%a: continue
        d=b*(z//a)
        for y in S:
            if y+d>n: break
            if y+d in Ss:
                T={y,y+d,z}
                kinds=sum(chain(t) for t in T)
                if mode=="nochainchain" and chain(y) and chain(y+d): continue
                if mode=="onlychainchain" and not (chain(y) and chain(y+d)): continue
                for c in range(3): cl.append([-v(t,c) for t in sorted(T)])
    f=f"/tmp/fx_{os.getpid()}.cnf"; open(f,"w").write(f"p cnf {3*len(S)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
    out=subprocess.run([CAD,"-q",f],capture_output=True,text=True).stdout
    return "UNSAT" if "s UNSAT" in out else "SAT"
if __name__=="__main__":
    for a,b in [(7,8),(10,11),(8,13),(15,17),(20,23),(16,25)]:
        n=N(a,b); print((a,b),n,'fixed all:',run(a,b,n),'N-1:',run(a,b,n-1),'| only chain-chain:',run(a,b,n,mode="onlychainchain"),'| no chain-chain:',run(a,b,n,mode="nochainchain"),flush=True)

import subprocess, os, sys
CAD="/home/claude/t/shim/cadical"
def maxfree(a,b,n):
    sols=set()
    for z in range(a,n+1,a):
        d=b*z//a
        for y in range(1,n-d+1): sols.add(tuple(sorted({y,y+d,z})))
    def sat(K):  # exists A with |A|>=K, no solution fully inside A
        nv=n; cl=[[-x for x in s] for s in sols]
        # sequential counter for sum x_i >= K  <=> sum (not x_i) <= n-K
        m=n-K; lits=[-(i) for i in range(1,n+1)]  # literal "not in A"
        if m<0: return False
        # Sinz encoding of at most m of lits
        s={}
        def var():
            nonlocal nv; nv+=1; return nv
        if m==0:
            for l in lits: cl.append([-l])
        else:
            for i in range(n):
                for j in range(m): s[i,j]=var()
            l=lits
            cl.append([-l[0],s[0,0]])
            for j in range(1,m): cl.append([-s[0,j]])
            for i in range(1,n):
                cl.append([-l[i],s[i,0]]); cl.append([-s[i-1,0],s[i,0]])
                for j in range(1,m):
                    cl.append([-l[i],-s[i-1,j-1],s[i,j]]); cl.append([-s[i-1,j],s[i,j]])
                cl.append([-l[i],-s[i-1,m-1]])
        f=f"/tmp/mx{os.getpid()}.cnf"; open(f,'w').write(f"p cnf {nv} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
        out=subprocess.run([CAD,"-q",f],capture_output=True,text=True).stdout
        return "UNSAT" not in out
    lo,hi=0,n
    while lo<hi:
        mid=(lo+hi+1)//2
        if sat(mid): lo=mid
        else: hi=mid-1
    return lo
if __name__=="__main__":
  for a,b in [(2,3)]:
      res=[(n,maxfree(a,b,n)) for n in (30,60,90)]
      print((a,b),res,'interval bound n*b/(a+b):',[round(n*b/(a+b),1) for n,_ in res],flush=True)

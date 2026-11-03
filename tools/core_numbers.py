import sys, subprocess, os, collections
CAD=os.path.expanduser('~/mnt/sat_solver/bin_linux/cadical'); DT=os.path.expanduser('~/mnt/sat_solver/bin_linux/drat-trim')
a,b,n=map(int,sys.argv[1:4])
v=lambda x,c: 3*(x-1)+c+1
cl=[]
for x in range(1,n+1): cl.append([v(x,0),v(x,1),v(x,2)])
s=1
while b*s<=n-1 and a*s<=n:
    d=b*s;z=a*s
    for y in range(1,n-d+1):
        S=sorted({y,y+d,z})
        for c in range(3): cl.append([-v(t,c) for t in S])
    s+=1
cl.append([v(1,0)])
with open('f.cnf','w') as f:
    f.write(f"p cnf {3*n} {len(cl)}\n"); f.writelines(" ".join(map(str,c))+" 0\n" for c in cl)
print('clauses',len(cl),flush=True)
r=subprocess.run([CAD,'-q','--no-binary','f.cnf','f.drat'],capture_output=True,text=True); print(r.stdout[-40:].strip())
r=subprocess.run([DT,'f.cnf','f.drat','-c','core.cnf','-t','2000'],capture_output=True,text=True); print(r.stdout[-300:])
nums=collections.Counter()
for l in open('core.cnf'):
    if l.startswith('p'): continue
    lits=[int(t) for t in l.split()[:-1]]
    for t in lits: nums[(abs(t)-1)//3+1]+=1
print('core numbers',len(nums),'of',n)
open('core_nums.txt','w').write(" ".join(map(str,sorted(nums))))

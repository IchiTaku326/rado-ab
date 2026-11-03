import sys, subprocess, os, collections
CAD=os.path.expanduser('~/mnt/sat_solver/bin_linux/cadical'); DT=os.path.expanduser('~/mnt/sat_solver/bin_linux/drat-trim')
a,b,n=map(int,sys.argv[1:4]); K=b*b+b+1; r=n%b
S=[x for x in range(1,n+1) if (x%a==0 and x<=a*K) or x%b==r]; idx={x:i+1 for i,x in enumerate(S)}; inset=set(S)
v=lambda x,c: 3*(idx[x]-1)+c+1
cl=[[v(x,0),v(x,1),v(x,2)] for x in S]; info=[None]*len(cl)
s=1
while b*s<=n-1 and a*s<=n:
    d=b*s;z=a*s
    if z in inset:
        for y in S:
            if y+d>n: break
            if y+d in inset:
                T=sorted({y,y+d,z})
                for c in range(3): cl.append([-v(t,c) for t in T]); info.append((y,y+d,z))
    s+=1
cl.append([v(S[0],0)]); info.append(None)
key={tuple(sorted(c)):i for i,c in enumerate(cl)}
open('g.cnf','w').write(f"p cnf {3*len(S)} {len(cl)}\n"+"".join(" ".join(map(str,c))+" 0\n" for c in cl))
print('S',len(S),'clauses',len(cl),flush=True)
subprocess.run([CAD,'-q','--no-binary','g.cnf','g.drat'],capture_output=True)
subprocess.run([DT,'g.cnf','g.drat','-c','gcore.cnf','-t','3000'],capture_output=True)
cnt=collections.Counter(); zs=collections.Counter(); ncore=0
for l in open('gcore.cnf'):
    if l.startswith('p'): continue
    c=tuple(sorted(int(t) for t in l.split()[:-1])); i=key.get(c)
    if i is None or info[i] is None: continue
    ncore+=1; y,x,z=info[i]
    cls=lambda t: ('M' if t%a==0 else '')+('C' if t%b==r else '')
    cnt[(cls(y),cls(x),cls(z))]+=1; zs[z//a]+=1
print('core triple clauses',ncore); print(cnt.most_common(8))
ds=sorted(zs); print('z/a used:',len(ds),'min',ds[0],'max',ds[-1], ds[:40])
# pairs in class-class clauses: p of smaller p (x side) and of larger
ps=[]
for l in open('gcore.cnf'):
    if l.startswith('p'): continue
    c=tuple(sorted(int(t) for t in l.split()[:-1])); i=key.get(c)
    if i is None or info[i] is None: continue
    y,x,z=info[i]
    if (y%b==r) and (x%b==r):
        px=(n-x)//b; py=(n-y)//b; ps.append((px,py,z//a))
L=(n-1)//b
import statistics
print('CC pairs',len(ps),'L',L)
print('min(px)',collections.Counter(min(p[0],L-p[1]) for p in ps).most_common(10))
hist=collections.Counter((p[0]*5//L, p[1]*5//L) for p in ps); print('px,py fifths',sorted(hist.items()))
pairs=set((p[0],p[1]) for p in ps); print('distinct pairs',len(pairs),'of possible',L*(L+1)//2)

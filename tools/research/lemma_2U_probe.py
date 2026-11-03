from math import gcd
def triples(a,b,n):
    T=[]
    for s in range(1,n+1):
        z=a*s; d=b*s
        if z>n: break
        for y in range(1,n-d+1):
            T.append(tuple(sorted({y,y+d,z})))
    return T
def propagate(asg,T):
    changed=True
    while changed:
        changed=False
        for t in T:
            vals=[asg.get(x) for x in t]
            for c in (0,1):
                # if all but one are c and the remaining unassigned -> it must be 1-c
                if sum(v==c for v in vals)==len(t)-1 and None in vals:
                    x=t[vals.index(None)]; asg[x]=1-c; changed=True; break
                if all(v==c for v in vals): return False
            if changed: break
    return True
def probe(a,b):
    n=b*(b+1); T=triples(a,b,n); asg={1:0}; order=[]
    assert propagate(asg,T)
    order.append(('start',sorted(asg.items())))
    level=0
    while len(asg)<n:
        found=False
        for x in range(1,n+1):
            if x in asg: continue
            for c in (0,1):
                t=dict(asg); t[x]=c
                if not propagate(t,T):
                    asg[x]=1-c; propagate(asg,T); order.append((x,1-c,len(asg))); found=True; break
            if found: break
        if not found:
            return order,asg,False
    return order,asg,True
for a,b in [(3,4),(3,5),(4,7),(3,7),(5,8)]:
    order,asg,done=probe(a,b)
    print((a,b),'done' if done else 'stuck', 'after unit prop from chi(1)=A:',len(order[0][1]),'assigned; probes:',[(o[0],o[1]) for o in order[1:]][:12],'... total probes',len(order)-1)

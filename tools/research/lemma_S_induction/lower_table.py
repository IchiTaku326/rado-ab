import sys, csv, os
from math import gcd
from multiprocessing import Pool
from lemS import *
def cell(ab):
    a,b=ab; R2=b*b+b+1; T=R2+2*a; K0=min(max(a*b+4*a,4*b),b*b+b)
    elems,copy,chain,sols=build(a,b,T); nE=len(elems)
    pat=lambda m: 0 if (m%a==0 and m//a<=b) else (1 if m<=b*b+b else 2)
    t0=next(t for t in range(a) if (1+b*t)%a==0)
    copyset={copy[m] for m in range(1,R2+1)}; spec={t for t in range(T) if t%a==t0}
    A={a*u2+b*u for u in range(1,b+1) for u2 in range(1,b+1)}
    rows=[]
    for m0 in range(a+1,K0+1):
        K=m0-1; want=pat(m0)
        for c in range(3):
            if c==want: continue
            f=lambda v,c=c:[[v(copy[m],pat(m))] for m in range(1,K+1)]+[[v(copy[m0],c)]]
            kind='copy' if solve(nE,sols,f,copyset) is None else None
            if not kind:
                for q in range(0,3):
                    W={q,q+a,q+2*a,q+m0,q+m0+a,q+m0+2*a}|spec
                    if max(W)<T and solve(nE,sols,f,copyset|{chain[t] for t in W}) is None: kind=f'W{q}'; break
            if not kind:
                kind='hard' if solve(nE,sols,f,set(range(nE))) is None else 'NOT_FORCED'
            typ='a*u' if want==0 else ('inA' if m0 in A else 'notA')
            rows.append((a,b,m0,c,typ,kind))
    return rows
if __name__=='__main__':
    bmax=int(sys.argv[1])
    cells=[(a,b) for b in range(3,bmax+1) for a in range(2,b) if gcd(a,b)==1 and a*a+(b-1)*a<=b*b+b+1]
    with Pool(4) as p, open('lower_table.csv','w',newline='') as fo:
        w=csv.writer(fo); w.writerow(['a','b','m','excluded_colour','type','proof'])
        for rows in p.imap_unordered(cell,cells):
            w.writerows(rows); fo.flush(); print(rows[0][:2] if rows else '', len(rows), flush=True)

# -*- coding: utf-8 -*-
r"""Task 2, upper bound for a whole family b = a + j by a SYMBOLIC SAT proof (Chang-De Loera-Wesley, arXiv:2210.03262, Lemma 4.5).
Elements are polynomials in a (coefficient lists, low degree first), indexed by (kind, qkind, q, r):
  chain  'ch': x = N(a) - b*p,  p = q*a + r  (qkind lo: q constant; hi: q = a + c)      N(a) = b(b^2+b+a+1) + a - j(j^2+j+1)
  multiple 'mu': x = a*m,       m = q*b + r  (same q kinds)                                with q in [0,Q1] U [a-Q2, a+7], |r| <= R.
At a = aref the elements in [1,N] are kept (equal polynomials merged); every solution triple found at aref is kept ONLY if it is a
polynomial identity a(x-y) = b z.  The CNF (3 colours, element 'a' has colour 0) is solved once (CaDiCaL).  Then a0 is computed:
for a >= a0 every element is in [1, N(a)] and all elements are pairwise different (root bounds of the difference polynomials).
Soundness: for every a >= a0 the same CNF is a sub-formula of "colour [1,N(a)] with 3 colours" (+ symmetry), so UNSAT => R3 <= N(a).
Writes results/sym_j{j}/ : family.cnf, elements.json (key -> polynomial), summary.txt.  Check the UNSAT with
cadical --lrat + lrat-check / cake_lpr (done for j = 1 on 2026-10-31: VERIFIED UNSAT by cake_lpr).
Run (Linux / WSL): python3 tools/sym_family.py j Q1 Q2 R aref      e.g.  1 10 10 12 60"""
import sys, subprocess, os, itertools, json
HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.environ.get("CADICAL", os.path.join(HERE, "..", "bin_linux", "cadical"))
def padd(p,q):
    n=max(len(p),len(q)); return [ (p[i] if i<len(p) else 0)+(q[i] if i<len(q) else 0) for i in range(n)]
def pmul(p,q):
    r=[0]*(len(p)+len(q)-1)
    for i,x in enumerate(p):
        for k,y in enumerate(q): r[i+k]+=x*y
    return r
def pneg(p): return [-x for x in p]
def pev(p,a): return sum(c*a**i for i,c in enumerate(p))
def ptrim(p):
    p=list(p)
    while len(p)>1 and p[-1]==0: p.pop()
    return p
def rootbound(p):
    p=ptrim(p)
    if len(p)==1: return 0
    lead=abs(p[-1]); return 1+max(abs(c) for c in p[:-1])//lead+1
def positive_from(p):
    """smallest A such that p(a) > 0 for all a >= A (p must have positive leading coeff), else None"""
    p=ptrim(p)
    if p[-1]<=0: return None
    B=rootbound(p)
    a=B
    while a>0 and pev(p,a-1)>0: a-=1     # walk down while still positive (not needed for soundness, only tightness)
    return max(a,0) if all(pev(p,t)>0 for t in range(a,B+1)) else B
def main(j,Q1,Q2,R,aref):
    A=[0,1]; b=[j,1]
    Np=padd(padd(pmul(b,padd(padd(pmul(b,b),b),[1,1])), [0,1]), [-j*(j*j+j+1)])   # N = b(b^2+b+a+1) + a - j(j^2+j+1)
    elems={}
    def qpoly(kind,q): return [q] if kind=="lo" else [q,1]          # lo: q ; hi: a + q
    for kind,qs in (("lo",range(0,Q1+1)),("hi",range(-Q2,8))):
        for q in qs:
            for r in range(-R,R+1):
                p=padd(pmul(qpoly(kind,q),A),[r])                     # position p = q*a + r
                elems[("ch",kind,q,r)]=padd(Np,pneg(pmul(b,p)))      # x = N - b p
                m=padd(pmul(qpoly(kind,q),b),[r])                     # m = q*b + r
                elems[("mu",kind,q,r)]=pmul(A,m)                     # x = a m
    # keep elements that are in [1, N] at aref; merge equal polynomials
    N0=pev(Np,aref); E={}
    for k,p in elems.items():
        p=tuple(ptrim(p)); x=pev(p,aref)
        if 1<=x<=N0 and p not in E.values(): E[k]=p
    keys=list(E); val={k:pev(E[k],aref) for k in keys}; byval={}
    for k in keys: byval.setdefault(val[k],[]).append(k)
    # clauses from triples at aref, kept only if a polynomial identity: a(x-y) = b z
    idx={k:i for i,k in enumerate(keys)}; v=lambda k,c:3*idx[k]+c+1
    cl=[[v(k,0),v(k,1),v(k,2)] for k in keys]
    one=[k for k in keys if E[k]==tuple(A)]; cl.append([v(one[0],0)])
    vals=sorted(byval); vs=set(vals); ntrip=0; nfake=0
    zs=[k for k in keys if val[k]%aref==0]
    for kz in zs:
        s=val[kz]//aref; d=(aref+j)*s
        for x0 in vals:
            if x0+d>N0: break
            if x0+d in vs:
                for ky in byval[x0]:
                    for kx in byval[x0+d]:
                        lhs=pmul(A,padd(list(E[kx]),pneg(list(E[ky])))); rhs=pmul(b,list(E[kz]))
                        if ptrim(padd(lhs,pneg(rhs)))!=[0]: nfake+=1; continue
                        T=sorted({ky,kx,kz},key=str); ntrip+=1
                        for c in range(3): cl.append([-v(t,c) for t in T])
    od=os.path.join(HERE,"..","results",f"sym_j{j}"); os.makedirs(od,exist_ok=True); f=os.path.join(od,"family.cnf")
    json.dump({str(k):list(E[k]) for k in keys},open(os.path.join(od,"elements.json"),"w"))
    with open(f,"w") as h:
        h.write(f"p cnf {3*len(keys)} {len(cl)}\n"); h.writelines(" ".join(map(str,c))+" 0\n" for c in cl)
    out=subprocess.run([CAD,"-q",f],capture_output=True,text=True,timeout=3000).stdout
    res="UNSAT" if "s UNSAT" in out else "SAT" if "s SAT" in out else "?"
    # a0: all elements >= 1 and <= N, pairwise distinct (as numbers), for a >= a0
    a0=0
    for k in keys:
        p=list(E[k]); t1=positive_from(padd(p,[-1])) if ptrim(padd(p,[-1]))!=[0] else 0
        t2=positive_from(padd(Np,pneg(p))) if ptrim(padd(Np,pneg(p)))!=[0] else 0
        if t1 is None or t2 is None: print("element not eventually in range:",k,p); return
        a0=max(a0,t1,t2)
    # distinctness: sort by leading behaviour; check all pairs via difference root bound (fast: only pairs with same degree/leading)
    P=sorted(set(E.values()))
    for p,q in itertools.combinations(P,2):
        d=ptrim(padd(list(p),pneg(list(q))))
        if d[-1]<0: d=pneg(d)
        t=positive_from(d); a0=max(a0,t)
    msg=f"j={j} Q1={Q1} Q2={Q2} R={R} aref={aref}: elements {len(keys)}, identity triples {ntrip} (coincidences dropped {nfake}), CNF {len(cl)} clauses -> {res}; valid for a >= {a0}"
    print(msg); open(os.path.join(od,"summary.txt"),"w").write(msg+"\n")
    return res,a0
if __name__=="__main__":
    main(*map(int,sys.argv[1:6]))

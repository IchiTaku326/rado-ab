# -*- coding: utf-8 -*-
r"""Symbolic case checker (a small "proof engine") for the lower-bound colourings of conjecture C, a = b - j:
   colour the numbers 1..n, n = b^3+2b^2-j^2(j+2)-1, by the template (v = a-adic valuation; h = top of colour 1 for v>=2):
     C0: v=0, x <= ab-1 | v=0, x >= n-2b | v>=2, x = a^2 u, 1 <= u <= b
     C1: v=1, x = a m, 1 <= m <= b(b+1) | v>=2, x = a^2 u, b+1 <= u <= b+h
     C2: v=0, ab <= x <= n-2b-1 | v=1, x = a m, m >= b(b+1)+1 | v>=2, x = a^2 u, u >= b+h+1
   (j=2, h=3: the theorem of 2026-10-28; j=3, h=4: found by MaxSAT.)
Every solution of a(x-y) = bz (gcd(a,b)=1) is z = a s, x - y = b s, so v(z) = 1 + v(s) and v(x-y) = v(s).
For every colour and every choice of pieces for x, y, z the script tries three SOUND lemmas, for ALL b >= b0 with gcd(b-j,b)=1:
  L1 divisibility: a | (x-y) is forced by the types of x, y (both multiples of a: yes; exactly one: no) and by z (v(z)=1: no; v(z)>=2: yes).
  L2 a^2: x, y both multiples of a^2 and v(z) >= 2  ->  a | u_z, so u_z >= a.
  L3 ranges: x - y lies in [Lx-Uy, Ux-Ly] and b*s in [b*smin, b*smax]; disjoint for all b >= b0 (polynomial inequality in b,
     proved by writing b = b0 + t and checking that every coefficient of the numerator is > 0, or by sympy's real roots).
Cases that none of the lemmas closes are printed as OPEN (they need a written argument, e.g. the residue argument for j=2)
and are checked numerically for b0 <= b <= bmax by brute force.  Needs: sympy (pip install sympy), numpy.
Env: ENDB (end block, default 2), NSHIFT (n lowered by NSHIFT*a, default 0).
Run: python tools\prove_lower.py J H b0 bmax [nstart]   e.g.  python tools\prove_lower.py 2 3 17 31 5
  (symbolic proof for all b >= b0; brute force for nstart <= b <= bmax, which covers the finitely many b < b0)"""
import itertools, math, os, sys
import sympy as sp

b, t = sp.symbols("b t", positive=True)


def positive_for_all(expr, b0):
    """True if the rational function expr(b) > 0 for every real b >= b0 (sufficient checks only)."""
    num, den = sp.fraction(sp.together(sp.expand(expr)))
    num = sp.Poly(sp.expand(num), b); den = sp.Poly(sp.expand(den), b)
    for p in (num, den):
        pass
    # denominators are products of powers of a = b - j > 0 for b >= b0: check the sign of den at b0 and that den has no root >= b0
    def no_root_and_positive(P):
        if P.is_zero: return False
        if P.degree() == 0: return P.LC() > 0
        sh = sp.Poly(sp.expand(P.as_expr().subs(b, b0 + t)), t)
        if all(c >= 0 for c in sh.all_coeffs()) and sh.eval(0) > 0: return True
        roots = [r for r in sp.real_roots(P)]
        return P.eval(b0) > 0 and all(r < b0 for r in roots)
    return no_root_and_positive(num) and no_root_and_positive(den)


def pieces(j, h, E=2):
    a = b - j
    n = b**3 + 2 * b**2 - j * j * (j + 2) - 1 - int(os.environ.get('NSHIFT', '0')) * a   # NSHIFT=1: one step lower (j=3, b>=43)
    # (colour, type, lower, upper) bounds of the NUMBER w (types: v0, v1 (w=a*m), v2 (w=a^2*u))
    return a, n, [
        (0, "v0", sp.Integer(1), a * b - 1), (0, "v0", n - E * b, n), (0, "v2", a**2, b * a**2),
        (1, "v1", a, a * b * (b + 1)), (1, "v2", (b + 1) * a**2, (b + h) * a**2),
        (2, "v0", a * b, n - E * b - 1), (2, "v1", a * (b * (b + 1) + 1), n), (2, "v2", (b + h + 1) * a**2, n),
    ]


def main():
    j, h, b0, bmax = map(int, sys.argv[1:5])
    nstart = int(sys.argv[5]) if len(sys.argv) > 5 else b0          # numeric brute force from here (covers b < b0 too)
    E = int(os.environ.get('ENDB', '2'))                           # end block of units: x >= n - E*b (j=2,3: 2; j=4: 6)
    a, n, P = pieces(j, h, E)
    closed, open_cases = 0, []
    for colour in range(3):
        pcs = [p for p in P if p[0] == colour]
        for ix, iy, iz in itertools.product(range(len(pcs)), repeat=3):
            px, py, pz = pcs[ix], pcs[iy], pcs[iz]
            if pz[1] == "v0":
                closed += 1; continue                                   # z = a s is never a unit
            desc = f"colour {colour}: x {px[1]}[{ix}] y {py[1]}[{iy}] z {pz[1]}[{iz}]"
            # L1
            mult_x, mult_y = px[1] != "v0", py[1] != "v0"
            need = (pz[1] == "v2")                                     # a | (x-y) ?
            if mult_x and mult_y and not need: print(desc, "-> closed by L1 (a|x-y, but v(z)=1)"); closed += 1; continue
            if mult_x != mult_y and need: print(desc, "-> closed by L1 (a does not divide x-y, but v(z)>=2)"); closed += 1; continue
            # bounds of s  (z = a s;  v1: s = m_z;  v2: s = a u_z)
            smin, smax = pz[2] / a, pz[3] / a
            L2 = (pz[1] == "v2" and px[1] == "v2" and py[1] == "v2")
            if L2:
                smin = a * a                                            # L2: a | u_z, u_z >= 1  ->  s = a u_z >= a^2  (smin above is <= a^2 here: pz[2] >= a^2)
                smin_alt = pz[2] / a
            dmax = px[3] - py[2]; dmin = px[2] - py[3]
            ok = False
            try:
                ok = positive_for_all(b * smin - dmax, b0) or (L2 and positive_for_all(b * smin_alt - dmax, b0)) \
                     or positive_for_all(dmin - b * smax, b0)
            except Exception:
                ok = False
            how = "L3 (ranges)" + (" + L2" if L2 else "")
            # L4 residue: x a multiple of a, y a unit with Ly = ab (residue 0 mod a), z of type v1 (s a unit).  For each of the
            # few possible s = smin + k (k = 0..K, K fixed by the ranges), x = y + b s = 0 (mod a) needs y = ab + r with
            # r = -j s = -j (j^2+j+1+k) (mod a)  [b = j mod a, s = b(b+1)+1+k];  the window r <= Ux - b s - ab must miss it.
            if not ok and mult_x and py[1] == "v0" and pz[1] == "v1" and sp.simplify(py[2] - a * b) == 0 and sp.simplify(pz[2] - a * (b * (b + 1) + 1)) == 0:
                K = None
                for kk in range(0, 6):
                    if positive_for_all(b * (b * (b + 1) + 1 + kk + 1) - dmax, b0): K = kk; break
                if K is not None:
                    good = True
                    for kk in range(K + 1):
                        need_r = a - j * (j * j + j + 1 + kk)                # smallest r >= 0 when a > j(j^2+j+1+k)
                        W = px[3] - b * (b * (b + 1) + 1 + kk) - a * b
                        if not (b0 - j > j * (j * j + j + 1 + kk) and positive_for_all(need_r - W, b0)):
                            good = False; break
                    if good:
                        ok = True; how = f"L4 (residue mod a, s = b(b+1)+1+k, k<={K})"
            if ok:
                print(desc, "-> closed by", how); closed += 1
            else:
                print(desc, "-> OPEN"); open_cases.append((colour, ix, iy, iz, desc))
    print(f"closed {closed}, OPEN {len(open_cases)}")
    # numeric check of the open cases (and of everything) by brute force for b0..bmax
    import numpy as np
    sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
    bad_any = False
    for bb in range(nstart, bmax + 1):
        aa = bb - j
        if aa < 2 or math.gcd(aa, bb) != 1: continue
        nn = bb**3 + 2 * bb * bb - j * j * (j + 2) - 1 - int(os.environ.get('NSHIFT', '0')) * aa
        col = np.zeros(nn + 1, dtype=np.int8)
        for x in range(1, nn + 1):
            e, y = 0, x
            while y % aa == 0: y //= aa; e += 1
            if e == 0: col[x] = 0 if (x <= aa * bb - 1 or x >= nn - E * bb) else 2
            elif e == 1: col[x] = 1 if x // aa <= bb * (bb + 1) else 2
            else:
                u = x // (aa * aa); col[x] = 0 if u <= bb else (1 if u <= bb + h else 2)
        bad = 0; s = 1
        while bb * s <= nn - 1 and aa * s <= nn:
            d = bb * s; z = aa * s; y = np.arange(1, nn - d + 1)
            bad += int(((col[y] == col[y + d]) & (col[y] == col[z])).sum()); s += 1
        print(f"  numeric b={bb}: {bad} monochromatic solutions")
        bad_any = bad_any or bad > 0
    print("NUMERIC: all 0" if not bad_any else "NUMERIC: violations found")


if __name__ == "__main__":
    main()

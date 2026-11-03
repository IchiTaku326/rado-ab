# -*- coding: utf-8 -*-
r"""ONE template for the whole region outside formula 1 (found 2026-10-29 from the e table):
   base(a,b) = b^3+2b^2 - (j-1)b + ((-j(j^2+j+1)) mod a),   j = b-a      (= N - j^2(j+2) - f*a, f = j-1-ceil(j(j^2+j+1)/a))
   colouring of [1, base-1]  (v = a-adic valuation, h = floor(b(b+1)/a) - b, i.e. colour 1 = multiples of a up to about ab(b+1)):
     C0: v=0 and (x <= ab-1 or x >= n-2b)  |  v>=2 and x/a^2 <= b
     C1: v=1 and x/a <= b(b+1)              |  v>=2 and b < x/a^2 <= b+h
     C2: the rest
   For large b (f >= 0) this is the template of the j=2,3,4 theorems (h = j+1).  Conjecture: no monochromatic solution for
   every 2 <= a < b, gcd(a,b)=1, outside formula 1 (a^2+(b-1)a > b^2+b+1)  ->  R3 >= base(a,b).
11 processes (multiprocessing), one row per cell in results\unified_template.csv (skipped on restart; Ctrl+C is safe),
progress with ETA.  Run: python tools\check_unified.py 5 80"""
import csv, math, os, sys, time
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
import numpy as np
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "unified_template.csv")


def base(a, b):
    j = b - a; c = j * (j * j + j + 1)
    return b ** 3 + 2 * b * b - (j - 1) * b + ((-c) % a)


def work(cell):
    a, b = cell; j = b - a; n = base(a, b) - 1; h = (b * (b + 1)) // a - b
    t0 = time.time()
    x = np.arange(n + 1, dtype=np.int64); v = np.zeros(n + 1, dtype=np.int8); t = x.copy(); t[0] = 1
    for _ in range(12):
        m = (t % a == 0)
        if not m.any(): break
        v[m] += 1; t[m] //= a
    c = np.full(n + 1, 2, np.int8)
    c[(v == 0) & ((x <= a * b - 1) | (x >= n - 2 * b))] = 0
    c[(v == 1) & (x // a <= b * (b + 1))] = 1
    q = x // (a * a); c[(v >= 2) & (q <= b)] = 0; c[(v >= 2) & (q > b) & (q <= b + h)] = 1
    del x, t, q
    # FFT: for every colour k, A_k(d) = #{y : c[y] = c[y+d] = k} for ALL d at once (autocorrelation), O(n log n)
    # instead of comparing arrays for every s (O(n^2/b)).  Monochromatic solutions = sum over s of A_{c[as]}(bs).
    L = 1 << (2 * (n + 1) - 1).bit_length()
    sv = np.arange(1, n // max(a, 1) + 1); sv = sv[b * sv <= n - 1]
    tot, first = 0, ""
    for k in range(3):
        ind = (c == k).astype(np.float64); ind[0] = 0.0
        F = np.fft.rfft(ind, L); A = np.fft.irfft(F * np.conj(F), L)[: n + 1]
        cnt = np.rint(A[b * sv]).astype(np.int64) * (c[a * sv] == k)
        tot += int(cnt.sum())
        if cnt.sum() and not first:
            s = int(sv[np.nonzero(cnt)[0][0]]); d = b * s; y = np.arange(1, n - d + 1)
            yy = int(y[(c[y] == k) & (c[y + d] == k)][0]); first = f"y={yy} x={yy + d} z={a * s}"
    return (a, b, j, j - 1 - (-(-j * (j * j + j + 1) // a)), h, n + 1, tot, first, round(time.time() - t0, 1))


def main():
    bmin, bmax = int(sys.argv[1]), int(sys.argv[2])
    W = int(sys.argv[3]) if len(sys.argv) > 3 else 11
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["a"]), int(r["b"])))
    cells = [(a, b) for b in range(bmax, bmin - 1, -1) for a in range(2, b)
             if math.gcd(a, b) == 1 and a * a + (b - 1) * a > b * b + b + 1 and (a, b) not in done]
    print(f"{len(cells)} cells to check ({len(done)} already done), {W} processes", flush=True)
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "j", "f", "h", "base", "violations", "first", "seconds"]); fh.flush()
    wt = {cl: float(cl[1]) ** 4 for cl in cells}; tot_w = sum(wt.values()) or 1; done_w = 0.0; t0 = time.time(); bad = 0
    with mp.Pool(W) as pool:
        for i, r in enumerate(pool.imap_unordered(work, cells), 1):
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")] + list(r)); fh.flush(); os.fsync(fh.fileno())
            done_w += wt[(r[0], r[1])]; bad += r[6] > 0
            el = time.time() - t0; eta = el / done_w * (tot_w - done_w)
            if r[6] > 0 or i % 10 == 0 or i == len(cells) or time.time() - getattr(main, "_last", 0) > 30:
                main._last = time.time()
                print(f"[{datetime.now(JST):%H:%M:%S}] {i}/{len(cells)}  ({r[0]},{r[1]}) j={r[2]} f={r[3]} h={r[4]} -> violations {r[6]} {r[7]}"
                      f"   | cells with violations so far: {bad} | elapsed {el/60:.0f} min, ETA about {eta/60:.0f} min", flush=True)
    print(f"done: {len(cells)} cells, with violations: {bad}  (results\\unified_template.csv)")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
r"""Lower bound for the cells with delta > 0 (found 2026-10-29 from the colourings of 70):
   HYBRID colouring = unified template (check_unified.py) + the whole END BLOCK  x > n-E  coloured 0.
   E = 0 is the unified template, E = ab is the formula-1 template, so the hybrid joins the two regions.
   For every cell of results\s_min3.csv with R_upper > base (delta > 0) it searches an E (0..ab) for which the hybrid colouring
   of [1, R_upper - 1] has no monochromatic solution (all solutions counted with FFT).  Found -> R >= R_upper, and with
   the subset upper bound R <= R_upper:  R = R_upper exactly.
11 processes, results\hybrid_check.csv (skipped on restart, Ctrl+C is safe), progress with ETA.
Run: python tools\check_hybrid.py [workers]"""
import csv, math, os, sys, time
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
import numpy as np
JST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "results", "hybrid_check.csv")


def base(a, b):
    j = b - a; return b ** 3 + 2 * b * b - (j - 1) * b + ((-j * (j * j + j + 1)) % a)


def parts(a, b, n):
    h = (b * (b + 1)) // a - b
    x = np.arange(n + 1, dtype=np.int64); v = np.zeros(n + 1, dtype=np.int8); t = x.copy(); t[0] = 1
    for _ in range(12):
        m = (t % a == 0)
        if not m.any(): break
        v[m] += 1; t[m] //= a
    c = np.full(n + 1, 2, np.int8)
    c[(v == 0) & ((x <= a * b - 1) | (x >= n - 2 * b))] = 0
    c[(v == 1) & (x // a <= b * (b + 1))] = 1
    q = x // (a * a); c[(v >= 2) & (q <= b)] = 0; c[(v >= 2) & (q > b) & (q <= b + h)] = 1
    return c


def mono(a, b, n, c):
    L = 1 << (2 * (n + 1) - 1).bit_length(); sv = np.arange(1, n // a + 1); sv = sv[b * sv <= n - 1]; tot = 0
    for k in range(3):
        ind = (c == k).astype(np.float64); ind[0] = 0.0
        F = np.fft.rfft(ind, L); A = np.fft.irfft(F * np.conj(F), L)[: n + 1]
        tot += int((np.rint(A[b * sv]).astype(np.int64) * (c[a * sv] == k)).sum())
    return tot


def work(cell):
    a, b, R = cell; n = R - 1; t0 = time.time(); c0 = parts(a, b, n); tried = 0
    order = []                                    # coarse grid first, then fine
    step = max(1, a // 2)
    order += list(range(0, a * b + 1, step)); order += [e for e in range(0, a * b + 1) if e % step]
    for E in order:
        c = c0.copy(); c[n - E + 1:] = 0; tried += 1
        if mono(a, b, n, c) == 0:
            return (a, b, R, E, tried, round(time.time() - t0, 1))
        if time.time() - t0 > 1800: break
    return (a, b, R, -1, tried, round(time.time() - t0, 1))


def main():
    W = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["a"]), int(r["b"])))
    cells = []
    for r in csv.DictReader(open(os.path.join(HERE, "..", "results", "s_min3.csv"), encoding="utf-8")):
        a, b, R = int(r["a"]), int(r["b"]), int(r["R_upper"])
        if R > base(a, b) and (a, b) not in done: cells.append((a, b, R))
    cells.sort(key=lambda t: -t[1])
    print(f"{len(cells)} cells with delta > 0 to check, {W} processes", flush=True)
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "R", "delta", "E", "tried", "seconds"]); fh.flush()
    wt = {cl: float(cl[1]) ** 4 for cl in cells}; tw = sum(wt.values()) or 1; dw = 0.0; t0 = time.time(); fail = 0
    with mp.Pool(W) as pool:
        for i, r in enumerate(pool.imap_unordered(work, cells), 1):
            a, b, R, E, tried, sec = r; d = (R - base(a, b)) // a
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), a, b, R, d, E, tried, sec]); fh.flush(); os.fsync(fh.fileno())
            dw += wt[(a, b, R)]; fail += E < 0; el = time.time() - t0
            print(f"[{datetime.now(JST):%H:%M:%S}] {i}/{len(cells)} ({a},{b}) delta={d}: E={E if E >= 0 else 'NOT FOUND'} ({tried} tried, {sec}s)"
                  f"  | not found so far {fail} | elapsed {el/60:.0f} min, ETA about {el/dw*(tw-dw)/60:.0f} min", flush=True)
    print(f"done: {len(cells)} cells, E not found: {fail}  (results\\hybrid_check.csv)")


if __name__ == "__main__":
    main()

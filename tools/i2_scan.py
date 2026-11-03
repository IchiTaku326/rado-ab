# -*- coding: utf-8 -*-
r"""Theorem R (k-induction lower bound) boundary scan (2026-11-02): for each cell 2 <= a < b, gcd = 1, in the formula-1 region,
check condition (I2) at k = 3..KMAX exactly: no m, s with T_(k-1)(m) = T_(k-1)(s) = 1 and M_k < a*m + b*s <= n_k
(M_k = b(L_(k-1) + a), n_k = b(L_(k-1) + 2a), L_2 = b^2+b+1, L_k = b(L_(k-1)+2a)+1).  If (I2) holds for k = 3..K then
R_k >= L_k for k <= K (Theorem R, hand proof).  Colour sets are built recursively (numpy bool arrays); a cell/k is skipped if
L_k > --maxlen.  The window test uses prefix sums (O(1) per s).  11 processes, results\i2_scan.csv (resumable), ETA.
Run: python tools\i2_scan.py --workers 8 --bmax 60 --kmax 6 --maxlen 120000000"""
import csv, os, sys, time
from math import gcd
from datetime import datetime, timezone, timedelta
import multiprocessing as mp
JST = timezone(timedelta(hours=9))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "i2_scan.csv")


def cell(arg):
    try:
        return cell0(arg)
    except MemoryError:
        a, b = arg[0], arg[1]
        return a, b, int(a * a + (b - 1) * a <= b * b + b + 1), int(a * a + a * b <= b * b), "", "", "MEMORY", 0.0


def cell0(arg):
    a, b, KMAX, MAXLEN = arg; t0 = time.time()
    import numpy as np
    L = {2: b * b + b + 1}
    for k in range(3, KMAX + 1): L[k] = b * (L[k - 1] + 2 * a) + 1
    n = L[2] - 1
    c0 = np.ones(n + 1, bool); c1 = np.zeros(n + 1, bool); c0[0] = False
    for u in range(1, b + 1): c1[a * u] = True; c0[a * u] = False
    res = {}; last_ok = 2
    for k in range(3, KMAX + 1):
        if L[k] > MAXLEN: res[k] = "SKIP"; break
        Lp = L[k - 1]; M = b * (Lp + a); nk = b * (Lp + 2 * a)
        # (I2) for step k uses colour-1 set of T_(k-1) = c1 (indices 1..Lp-1)
        S = np.nonzero(c1)[0]
        pref = np.concatenate(([0], np.cumsum(c1, dtype=np.int64)))      # pref[i] = #c1 in [0, i-1]
        ok = True
        for s in S:
            lo = (M - b * int(s)) // a + 1; hi = (nk - b * int(s)) // a
            lo = max(lo, 1); hi = min(hi, len(c1) - 1)
            if lo <= hi and pref[hi + 1] - pref[lo] > 0: ok = False; break
        res[k] = "OK" if ok else "FAIL"
        if not ok: break
        last_ok = k
        if k == KMAX: break
        # build T_k colour sets on [1, L_k - 1]
        nn = L[k] - 1                                                  # (11-02: no big arange -> 8x less memory)
        n0 = np.zeros(nn + 1, bool); n1 = np.zeros(nn + 1, bool)
        small = np.arange(a * b); n0[:a * b] = (small % a != 0); n0[M + 1:] = True
        ms = np.arange(1, Lp)
        n0[a * ms[c1[1:Lp]]] = True; n1[a * ms[c0[1:Lp]]] = True
        n0[0] = False; c0, c1 = n0, n1
    f1 = a * a + (b - 1) * a <= b * b + b + 1; g = a * a + a * b <= b * b
    first_fail = next((k for k, v in res.items() if v == "FAIL"), "")
    return a, b, int(f1), int(g), last_ok, first_fail, " ".join(f"{k}:{v}" for k, v in res.items()), round(time.time() - t0, 1)


def main():
    args = sys.argv[1:]; W, B, K, ML = 11, 60, 6, 200_000_000
    while args:
        k_, v_ = args[0], args[1]; args = args[2:]
        if k_ == "--workers": W = int(v_)
        elif k_ == "--bmax": B = int(v_)
        elif k_ == "--kmax": K = int(v_)
        elif k_ == "--maxlen": ML = int(v_)
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")): done.add((int(r["a"]), int(r["b"])))
    jobs = [(a, b, K, ML) for b in range(3, B + 1) for a in range(2, b) if gcd(a, b) == 1 and a * a + (b - 1) * a <= b * b + b + 1 and (a, b) not in done]
    new = not os.path.exists(OUT); fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "a", "b", "f1", "golden", "I2_holds_up_to_k", "first_fail_k", "detail", "seconds"]); fh.flush()
    print(f"{len(jobs)} cells ({len(done)} done), {W} processes, k <= {K}, max length {ML}", flush=True)
    t0 = time.time(); wt = sum(b ** 4 for a, b, _, _ in jobs); wd = 0
    with mp.Pool(W) as pool:
        for i, r in enumerate(pool.imap_unordered(cell, jobs), 1):
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), *r]); fh.flush(); os.fsync(fh.fileno())
            wd += r[1] ** 4; el = time.time() - t0
            print(f"[{datetime.now(JST):%H:%M:%S}] {i}/{len(jobs)} ({r[0]},{r[1]}) golden={r[3]} ok up to k={r[4]} fail={r[5]} {r[7]}s | ETA about {el/max(wd,1)*(wt-wd)/60:.0f} min", flush=True)
    print("done (results\\i2_scan.csv)")


if __name__ == "__main__":
    mp.freeze_support(); main()

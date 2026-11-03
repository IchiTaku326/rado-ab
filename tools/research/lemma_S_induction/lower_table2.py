#!/usr/bin/env python3
"""lower_table2.py -- 補題 S の「下の補題」の歩を、式1 の領域の全ての組 (b <= BMAX) で分類する (2026-11-02)。
各組 (a,b) で、簡約した「列 + コピー」の問題 (列の長さ T = R2+2a) を作り、
  m = a+1 .. K0 (= max(ab+4a, 4b)) の各歩・各「除く色」について、
  [1, m-1] を型 P に固定したとき φ(m) = その色 が矛盾するのは
    copy  : コピーだけで矛盾
    W0..W2: 型 W (列の位置 q, q+a, q+2a, q+m, q+m+a, q+m+2a と特別な位置) で矛盾
    hard  : 列の全体を使って初めて矛盾
    NOT_FORCED : 矛盾しない
  を調べる。さらに各組で「φ を [1,K0] で型に決めるのに要る最短の列の長さ」(minL) も求める。
止めて続きから: 組ごとのファイル results/lemmaS/lower_a{a}_b{b}.csv に 1 歩ずつ追記 (flush + fsync)、再実行で済んだ歩は飛ばす。
失われるのは実行中の 1 回の SAT 判定だけ (1 回は数秒〜数十秒)。
使い方: python3 lower_table2.py --bmax 17 --workers 11 --cadical bin_linux/cadical
"""
import argparse, csv, itertools, os, subprocess, sys, tempfile, time
from math import gcd
from multiprocessing import Pool

OUT = "results/lemmaS"
G = {}

def build(a, b, T):
    R2 = b*b+b+1
    num, elems = {}, []
    def el(n):
        if n not in num:
            num[n] = len(elems); elems.append(n)
        return num[n]
    copy = {m: el(a*m) for m in range(1, R2+1)}
    chain = {t: el(1+b*t) for t in range(T)}
    sols = set()
    for s in range(1, R2+1):
        if a*s > R2: break
        for Y in range(1, R2+1):
            X = Y + b*s
            if X > R2: break
            sols.add((copy[X], copy[Y], copy[a*s]))
    for t in range(T):
        for u in range(t+1, min(T, t+R2+1)):
            sols.add((chain[u], chain[t], copy[u-t]))
    return len(elems), copy, chain, sorted(sols)

def solve(nE, sols, fixed, keep, timeout=900):
    v = lambda e, c: e*3 + c + 1
    lines = []
    for e in keep:
        lines.append(f"{v(e,0)} {v(e,1)} {v(e,2)} 0")
        for c1, c2 in ((0,1),(0,2),(1,2)):
            lines.append(f"-{v(e,c1)} -{v(e,c2)} 0")
    for (x, y, z) in sols:
        if x in keep and y in keep and z in keep:
            for c in range(3):
                lits = sorted({-v(x,c), -v(y,c), -v(z,c)})
                lines.append(" ".join(map(str, lits)) + " 0")
    for cl in fixed(v):
        lines.append(" ".join(map(str, cl)) + " 0")
    fd, fn = tempfile.mkstemp(suffix=".cnf", dir=G["tmp"])
    with os.fdopen(fd, "w") as f:
        f.write(f"p cnf {nE*3} {len(lines)}\n"); f.write("\n".join(lines)); f.write("\n")
    try:
        r = subprocess.run([G["cad"], "-q", fn], capture_output=True, text=True, timeout=timeout)
        rc = r.returncode
    except subprocess.TimeoutExpired:
        rc = 0
    finally:
        os.unlink(fn)
    return {10: "SAT", 20: "UNSAT"}.get(rc, "TIMEOUT")

def cell_params(a, b):
    R2 = b*b+b+1; T = R2+2*a; K0 = min(max(a*b+4*a, 4*b), b*b+b)
    return R2, T, K0

def cell(ab):
    a, b = ab
    R2, T, K0 = cell_params(a, b)
    fn = os.path.join(OUT, f"lower_a{a}_b{b}.csv")
    done = set()
    if os.path.exists(fn):
        for r in csv.reader(open(fn)):
            if r and r[0] != "m": done.add((int(r[0]), int(r[1])))
    if (-1, -1) in done: return ab
    nE, copy, chain, sols = build(a, b, T)
    pat = lambda m: 0 if (m % a == 0 and m//a <= b) else (1 if m <= b*b+b else 2)
    t0 = next(t for t in range(a) if (1+b*t) % a == 0)
    copyset = {copy[m] for m in range(1, R2+1)}
    spec = {t for t in range(T) if t % a == t0}
    A = {a*u2+b*u for u in range(1, b+1) for u2 in range(1, b+1)}
    allk = set(range(nE))
    new = not os.path.exists(fn)
    fo = open(fn, "a", newline=""); w = csv.writer(fo)
    if new: w.writerow(["m", "excluded_colour", "type", "proof", "seconds"])
    def put(row):
        w.writerow(row); fo.flush(); os.fsync(fo.fileno())
    for m0 in range(a+1, K0+1):
        want = pat(m0)
        for c in range(3):
            if c == want or (m0, c) in done: continue
            t1 = time.time()
            f = lambda v, c=c, m0=m0: [[v(copy[m], pat(m))] for m in range(1, m0)] + [[v(copy[m0], c)]]
            kind = "copy" if solve(nE, sols, f, copyset) == "UNSAT" else None
            if not kind:
                for q in range(3):
                    W = {q, q+a, q+2*a, q+m0, q+m0+a, q+m0+2*a} | spec
                    if max(W) < T and solve(nE, sols, f, copyset | {chain[t] for t in W}) == "UNSAT":
                        kind = f"W{q}"; break
            if not kind:
                r = solve(nE, sols, f, allk)
                kind = {"UNSAT": "hard", "SAT": "NOT_FORCED"}[r] if r != "TIMEOUT" else "TIMEOUT"
            typ = "a*u" if want == 0 else ("inA" if m0 in A else "notA")
            put([m0, c, typ, kind, f"{time.time()-t1:.1f}"])
    # minimal chain length forcing the pattern on [1,K0] (binary search; recorded as m=0)
    if (0, 0) not in done:
        t1 = time.time()
        def forced(L):
            keep = copyset | {chain[t] for t in range(L)}
            f = lambda v: [[v(copy[1], 1)], [v(copy[a], 0)], [-v(copy[m], pat(m)) for m in range(2, K0+1)]]
            return solve(nE, sols, f, keep) == "UNSAT"
        if forced(T):
            lo, hi = 0, T
            while lo < hi:
                mid = (lo+hi)//2
                if forced(mid): hi = mid
                else: lo = mid+1
            res = lo
        else:
            res = "NOT_FORCED"
        put([0, 0, "minL", res, f"{time.time()-t1:.1f}"])
    put([-1, -1, "cell", "DONE", ""])
    fo.close()
    return ab

def init(cad, tmp):
    import signal; signal.signal(signal.SIGINT, signal.SIG_IGN)   # 子は Ctrl+C を無視し、親が pool を止める
    G["cad"] = cad; G["tmp"] = tmp

def count_rows(a, b):
    fn = os.path.join(OUT, f"lower_a{a}_b{b}.csv")
    if not os.path.exists(fn): return 0, False
    rows = list(csv.reader(open(fn)))[1:]
    return sum(1 for r in rows if r and int(r[0]) > 0), any(r and r[0] == "-1" for r in rows)

def summary(cells):
    lines = ["下の補題の歩の分類 (lower_table2.py)。hard = 列の全体を使って初めて矛盾、NOT_FORCED = 矛盾しない (補題が偽)。",
             "列: (a,b) R2 K0 | hard の数 / 歩の数 | minL(型を [1,K0] で決める最短の列) | hard の歩 (m:除く色:種類)"]
    for a, b in cells:
        fn = os.path.join(OUT, f"lower_a{a}_b{b}.csv")
        if not os.path.exists(fn): continue
        rows = [r for r in csv.DictReader(open(fn)) if int(r["m"]) > 0]
        mins = [r["proof"] for r in csv.DictReader(open(fn)) if r["m"] == "0"]
        R2, T, K0 = cell_params(a, b)
        hard = [f'{r["m"]}:{r["excluded_colour"]}:{r["type"]}' for r in rows if r["proof"] in ("hard", "NOT_FORCED", "TIMEOUT")]
        lines.append(f"({a},{b}) R2={R2} K0={K0} | hard {len(hard)}/{len(rows)} | minL {mins[0] if mins else '?'} | {' '.join(hard)}")
    open(os.path.join(OUT, "LOWER_SUMMARY.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return lines

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bmax", type=int, default=17); ap.add_argument("--bmin", type=int, default=3)
    ap.add_argument("--workers", type=int, default=11); ap.add_argument("--cadical", default="bin_linux/cadical")
    A = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    tmp = "/tmp/lower_table2"; os.makedirs(tmp, exist_ok=True)
    cad = os.path.join(tmp, "cadical")
    if not os.path.exists(cad):
        import shutil; shutil.copy(A.cadical, cad); os.chmod(cad, 0o755)
    cells = [(a, b) for b in range(A.bmin, A.bmax+1) for a in range(2, b)
             if gcd(a, b) == 1 and a*a+(b-1)*a <= b*b+b+1]
    weight = {ab: (cell_params(*ab)[1]*cell_params(*ab)[0])*(cell_params(*ab)[2]) for ab in cells}
    steps = {ab: 2*(cell_params(*ab)[2]-ab[0]) for ab in cells}
    todo = [ab for ab in cells if not count_rows(*ab)[1]]
    todo.sort(key=lambda ab: -weight[ab])
    tot_w = sum(weight[ab]*(1-count_rows(*ab)[0]/max(1, steps[ab])) for ab in todo)
    print(f"[{time.strftime('%m-%d %H:%M:%S')}] 式1 の領域 {len(cells)} 組 (b {A.bmin}..{A.bmax})、残り {len(todo)} 組、{A.workers} 並列。結果 {OUT}/", flush=True)
    t0 = time.time(); start_done = {ab: count_rows(*ab)[0] for ab in todo}
    pool = Pool(A.workers, initializer=init, initargs=(cad, tmp))
    try:
        res = pool.map_async(cell, todo)
        while not res.ready():
            res.wait(60)
            dw = 0.0; nd = 0
            for ab in todo:
                k, fin = count_rows(*ab)
                if fin: nd += 1
                dw += weight[ab]*(max(0, min(k, steps[ab]) - start_done[ab]))/max(1, steps[ab])
            el = time.time()-t0
            eta = (el/dw*(tot_w-dw)/60) if dw > 0 else float('nan')
            print(f"[{time.strftime('%m-%d %H:%M:%S')}] 組 {nd}/{len(todo)} 完了、経過 {el/60:.0f} 分、残り 約 {eta:.0f} 分 (大まかな目安)", flush=True)
        res.get(); pool.close(); pool.join()
    except KeyboardInterrupt:
        pool.terminate(); pool.join()
        print("止めた (Ctrl+C)。済んだ歩は保存済み。同じコマンドで続きから。", flush=True); sys.exit(1)
    for line in summary(cells): print(line)
    print(f"結果のまとめ: {OUT}/LOWER_SUMMARY.txt")

if __name__ == "__main__":
    main()

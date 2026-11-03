# -*- coding: utf-8 -*-
r"""Item 3 (2026-11-02 JST): grow a subset S' of [1,n] until it has no good k-colouring (an upper-bound candidate R_k <= n),
or until a good colouring of S' extends to all of [1,n] (then R_k > n, colouring checked directly and saved).
Start: S = {multiples of a} ∪ {x ≡ n (mod b)} (the small set with K = all; for (3,5) n=961 and (2,5) n=926 it is colourable).
Each round: (1) find a good colouring of S' — the formula is split into first-fit cubes (the first D elements of S') solved in
parallel by CaDiCaL (--workers, default 11); (2) propagate it to [1,n] (a number that would complete a monochromatic solution
loses that colour; one colour left -> forced); a number with no colour left = conflict -> add it and the forced numbers to S';
(3) if there is no conflict, solve [1,n] with S' fixed (if SAT: a colouring of [1,n] -> R_k > n).
Resumable: results\cegar\cegar_a{a}_b{b}_k{k}_n{n}.json keeps S' and the round number.  Ctrl+C is safe (state saved each round).
The number of rounds is not known in advance, so no ETA for the end: each round prints its time, |S'| and the rounds so far.
v2 (11-02 14:30): a round first tries to REPAIR the previous colouring (only numbers near the new ones are re-coloured;
usually seconds) and uses the full parallel cube solve only if that fails; all conflicts of a propagation pass are added at once.
v3 (11-02 16:00): results\cegar\RESULT_*.txt says in plain words what the outcome means; progress shows |S'|/n,
the trend and a rough upper time estimate; --max-hours stops a job (resumable) so the next job gets its turn.
Run inside WSL: python3 tools/research/cegar_subset.py 3 5 4 961 [--workers 11] [--depth 6] [--cube-wall 1800]"""
import subprocess, sys, os, json, time, shutil, tempfile, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9)); now = lambda: datetime.now(JST).strftime("%m-%d %H:%M:%S")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
ap = argparse.ArgumentParser(); ap.add_argument("a", type=int); ap.add_argument("b", type=int); ap.add_argument("k", type=int); ap.add_argument("n", type=int)
ap.add_argument("--workers", type=int, default=11); ap.add_argument("--depth", type=int, default=6); ap.add_argument("--cube-wall", type=int, default=1800)
ap.add_argument("--cadical", default=""); ap.add_argument("--max-add", type=int, default=30)
ap.add_argument("--max-hours", type=float, default=0, help="stop (resumable) after this many hours; 0 = no limit"); A = ap.parse_args()
a, b, k, n = A.a, A.b, A.k, A.n
cad = A.cadical
if not cad:
    cad = os.path.join(tempfile.gettempdir(), "cg_cadical"); shutil.copy(os.path.join(ROOT, "bin_linux", "cadical"), cad); os.chmod(cad, 0o755)
OUTD = os.path.join(ROOT, "results", "cegar"); os.makedirs(OUTD, exist_ok=True)
ST = os.path.join(OUTD, f"cegar_a{a}_b{b}_k{k}_n{n}.json")
sols = []
for z in range(a, n + 1, a):
    if (b * z) % a: continue
    d = b * z // a
    for y in range(1, n - d + 1):
        x = y + d; assert a * (x - y) == b * z; sols.append((x, y, z))
by = {}
for s in sols:
    for t in set(s): by.setdefault(t, []).append(s)

def cnf(S, fixed=None):
    idx = {x: i for i, x in enumerate(S)}; v = lambda x, c: k * idx[x] + c + 1
    cl = [[v(x, c) for c in range(k)] for x in S]
    if fixed is None:
        for i, x in enumerate(S[:k]):
            for c in range(i + 1, k): cl.append([-v(x, c)])                  # first fit (w.l.o.g.)
    else:
        for x, c in fixed.items():
            if x in idx: cl.append([v(x, c)])
    for (x, y, z) in sols:
        if x in idx and y in idx and z in idx:
            T = sorted({x, y, z})
            for c in range(k): cl.append([-v(t, c) for t in T])
    return idx, v, cl

import threading
PROCS = set(); STOP = threading.Event(); PL = threading.Lock()
def run_cnf(cl, nv, extra, wall):
    if STOP.is_set(): return "CANCELLED", None
    fd, f = tempfile.mkstemp(suffix=".cnf"); os.close(fd)
    try:
        with open(f, "w") as fh:
            fh.write(f"p cnf {nv} {len(cl) + len(extra)}\n"); fh.writelines(" ".join(map(str, c)) + " 0\n" for c in cl + extra)
        p = subprocess.Popen([cad, "-q", f], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        with PL: PROCS.add(p)
        try:
            out, _ = p.communicate(timeout=wall)
        except subprocess.TimeoutExpired:
            p.kill(); p.communicate(); return "TIMEOUT", None
        finally:
            with PL: PROCS.discard(p)
        if STOP.is_set() and p.returncode not in (10, 20): return "CANCELLED", None
        st = [l for l in out.splitlines() if l.startswith("s ")]
        if not st: return "ERROR", None
        if "UNSAT" in st[0]: return "UNSAT", None
        return "SAT", set(int(t) for l in out.splitlines() if l.startswith("v") for t in l.split()[1:] if int(t) > 0)
    finally:
        os.remove(f)

def firstfit(D):
    out = [[]]
    for i in range(D):
        out = [p + [c] for p in out for c in range(min(k, (max(p) + 2) if p else 1))]
    return out

def colour_S(S, prev=None):
    idx, v, cl = cnf(S); nv = k * len(S)
    cubes = firstfit(min(A.depth, len(S))); res = {}; found = None; STOP.clear()
    if prev:                                   # v2: the cube that matches the previous colouring (renamed first-fit) goes first
        ren = {}; pre = []
        for x in S[:min(A.depth, len(S))]:
            c = prev.get(x)
            if c is None: break
            if c not in ren: ren[c] = len(ren)
            pre.append(ren[c])
        cubes.sort(key=lambda cu: [abs(p - q) for p, q in zip(cu, pre)] if pre else 0)
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        fut = {ex.submit(run_cnf, cl, nv, [[v(S[i], c)] for i, c in enumerate(cu)], A.cube_wall): tuple(cu) for cu in cubes}
        try:
            for fu in as_completed(fut):
                st, val = fu.result(); res[fut[fu]] = st
                if st == "SAT" and found is None:
                    found = {x: next(c for c in range(k) if v(x, c) in val) for x in S}
                    STOP.set()
                    for f2 in fut: f2.cancel()
                    with PL:
                        for p in list(PROCS): p.kill()
                    break
        except KeyboardInterrupt:                 # v3: kill the solvers first, so Ctrl+C does not wait for running cubes
            STOP.set()
            for f2 in fut: f2.cancel()
            with PL:
                for p in list(PROCS): p.kill()
            raise
    STOP.clear()
    if found: return "SAT", found
    if all(s == "UNSAT" for s in res.values()) and len(res) == len(cubes): return "UNSAT", None
    return "UNKNOWN", None

def repair(S, prev, newel):
    """11-02 v2: keep the previous colouring on most of S' and re-colour only the numbers near the new ones
    (radius 1, then 2: numbers sharing a solution).  Small SAT problems, usually seconds."""
    if not prev: return None
    Sset = set(S); near = set(newel)
    for rad in (1,):                       # larger radii free almost everything (dense solutions): no gain
        for x in list(near):
            for sol in by.get(x, []):
                near |= {t for t in sol if t in Sset}
        fixed = {x: c for x, c in prev.items() if x in Sset and x not in near}
        idx, v, cl = cnf(S, fixed=fixed)
        r, val = run_cnf(cl, k * len(S), [], 300)
        if r == "SAT":
            return {x: next(c for c in range(k) if v(x, c) in val) for x in S}
        print(f"[{now()}]   (前の塗り方の近く {len(near)} 個だけ塗り直す: {'無理' if r == 'UNSAT' else r} -> S' 全体を {A.workers} 並列で解く)", flush=True)
    return None

def propagate(col):
    cur = dict(col); allow = {x: set(range(k)) for x in range(1, n + 1) if x not in cur}; added = []; confl = []
    changed = True
    while changed:
        changed = False
        for x in list(allow):
            if x in cur: continue
            for (p, q, r) in by.get(x, []):
                o = [t for t in (p, q, r) if t != x]
                if all(t in cur for t in o) and len({cur[t] for t in o}) == 1: allow[x].discard(cur[o[0]])
            if not allow[x]:
                if x not in confl: confl.append(x)
                continue
            if len(allow[x]) == 1: cur[x] = next(iter(allow[x])); added.append(x); changed = True
    if confl: return confl, added
    global ALLOW; ALLOW = {x: len(c) for x, c in allow.items() if x not in cur}
    return [], added

def check(col):
    return all(not (col[x] == col[y] == col[z]) for (x, y, z) in sols)

RES = os.path.join(OUTD, f"RESULT_a{a}_b{b}_k{k}_n{n}.txt")
def write_result(kind, detail):
    """v3 (11-02): a plain result file that says what the outcome MEANS (Japanese + English)."""
    J = {"UPPER": f"【結果】S'({len(S)} 個の数)は {k} 色で塗れない。→ R{k}({a},{b}) ≤ {n} の「候補」。\n"
                  f"  まだ証明ではない: この S' を分割探索 + LRAT + cake_lpr で検査すれば証明になる(次の作業)。\n"
                  f"  予想の値 {n} が正しければ、R{k}({a},{b}) = {n} が確定する(下界の塗り方は既にある)。",
         "LOWER": f"【結果】[1,{n}] 全体の {k} 色の良い塗り方が見つかり、全ての解で直接検査した。→ R{k}({a},{b}) > {n}(証明つき)。\n"
                  f"  予想の値 {n} は外れ。塗り方は results\\c1_k4ab\\cert_a{a}_b{b}_k{k}_n{n}_cegar.json。",
         "OPEN":  f"【結果】まだ決着していない(途中で止めた/時間切れ/キューブの時間切れ)。|S'| = {len(S)} / {n}。\n"
                  f"  同じコマンドで続きから再開できる。"}[kind]
    E = {"UPPER": f"S' ({len(S)} numbers) has no good {k}-colouring: upper-bound candidate R{k}({a},{b}) <= {n} (proof still to be produced).",
         "LOWER": f"good {k}-colouring of [1,{n}] found and checked: R{k}({a},{b}) > {n}.",
         "OPEN":  f"undecided; |S'| = {len(S)} of {n}; resume with the same command."}[kind]
    rounds = st.get("round", 0); hrs = sum(x[2] for x in st.get("log", [])) / 3600
    txt = (f"R{k}({a}(x-y)={b}z), n = {n}   [{now()} JST]\n{J}\n{E}\n"
           f"回数 rounds: {rounds}、計算時間の合計 total time: {hrs:.1f} h\n" + (f"詳細: {detail}\n" if detail else ""))
    open(RES, "w", encoding="utf-8").write(txt)
    print("\n" + "=" * 70 + "\n" + txt + "=" * 70, flush=True)
    if kind != "OPEN": st["result"] = E
    json.dump(st, open(ST, "w"))

def save_full(colf):
    out = os.path.join(ROOT, "results", "c1_k4ab", f"cert_a{a}_b{b}_k{k}_n{n}_cegar.json"); os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"a": a, "b": b, "k": k, "n": n, "coloring": [colf[x] for x in range(1, n + 1)], "method": "cegar"}, open(out, "w"))

def progress_line(newel, secs):
    """|S'| progress, the trend of the last 5 rounds, and a rough UPPER estimate of the remaining time
    (S' can grow at most to n; the run usually ends earlier, when S' becomes uncolourable)."""
    lg = st["log"][-5:]
    pct = 100.0 * len(S) / n
    msg = f"[{now()}] 回 {st['round']}: +{len(newel)} 個 -> |S'| = {len(S)} / {n} ({pct:.0f}%), この回 {secs/60:.1f} 分"
    if len(lg) >= 2:
        add = (lg[-1][1] - lg[0][1]) / (len(lg) - 1); sec = sum(x[2] for x in lg[1:]) / (len(lg) - 1)
        if add > 0:
            rest = (n - len(S)) / add * sec / 3600
            msg += f" | 直近: 1 回 +{add:.0f} 個・{sec/60:.1f} 分 -> 全部入るまで最大 約 {rest:.1f} 時間(多くはその前に決着)"
    print(msg, flush=True)

st = json.load(open(ST)) if os.path.exists(ST) else {"S": sorted(set(x for x in range(1, n + 1) if x % a == 0 or x % b == n % b)), "round": 0, "log": []}
if st.get("result"):
    print(f"[{now()}] 既に決着済み already finished: {st['result']}", flush=True)
    if os.path.exists(RES): print(open(RES, encoding="utf-8").read(), flush=True)
    sys.exit(0)
S = st["S"]; t0 = time.time()
print(f"[{now()}] R{k}({a}(x-y)={b}z), n = {n}: 回 {st['round']+1} から開始、|S'| = {len(S)} / {n}、{A.workers} 並列"
      + (f"、最長 {A.max_hours} 時間" if A.max_hours else ""), flush=True)
print(f"  意味: S' が塗れなくなれば R{k} ≤ {n} の候補、[1,{n}] 全体の塗り方が見つかれば R{k} > {n}。", flush=True)
try:
    while True:
        if A.max_hours and time.time() - t0 > A.max_hours * 3600:
            write_result("OPEN", f"--max-hours {A.max_hours} に達したので止めた"); break
        tr = time.time(); st["round"] += 1
        col = None; prev = None
        if st.get("col"):
            prev = {int(x): c for x, c in st["col"].items()}
            if set(prev) >= set(S): col = {x: prev[x] for x in S}; res = "SAT"          # stored colouring of this S'
            else: col = repair(S, prev, sorted(set(S) - set(prev))); res = "SAT" if col else None
        if col is None: res, col = colour_S(S, prev)
        if res == "SAT": st["col"] = {str(x): c for x, c in col.items()}
        if res == "UNSAT":
            write_result("UPPER", ""); break
        if res == "UNKNOWN":
            st["round"] -= 1
            write_result("OPEN", f"キューブが時間切れ ({A.cube_wall} 秒) で塗り方が見つからなかった。--depth {A.depth+2} か --cube-wall を大きくして再実行"); break
        if len(S) == n:
            assert check(col); save_full(col); write_result("LOWER", ""); break
        conf, added = propagate(col)
        if not conf:
            full = list(range(1, n + 1)); idx, v, cl = cnf(full, fixed=col)
            r2, val = run_cnf(cl, k * n, [], 4 * A.cube_wall)
            if r2 == "SAT":
                colf = {x: next(c for c in range(k) if v(x, c) in val) for x in full}
                assert check(colf); save_full(colf); write_result("LOWER", ""); break
            rest = sorted(ALLOW, key=lambda x: ALLOW[x])
            newel = set(added) | set(rest[:max(20, len(rest) // 10)])        # the most constrained numbers
            print(f"[{now()}]   (矛盾は直接は出ないが、S' を固定すると全体が {r2}: 色の選択肢が少ない数を {len(newel)} 個足す)", flush=True)
        else:
            newel = set(conf[:A.max_add]) | set(added[:max(0, A.max_add - len(conf))])   # v2: small steps keep the repair local
            if not newel: newel = set(conf) | set(added)
        S = sorted(set(S) | newel); st["S"] = S
        st["log"].append([now(), len(S), round(time.time() - tr)]); json.dump(st, open(ST, "w"))
        progress_line(newel, time.time() - tr)
except KeyboardInterrupt:
    STOP.set(); st["round"] = max(0, st["round"] - 1)      # the interrupted round is not counted
    with PL:
        for p in list(PROCS): p.kill()
    write_result("OPEN", "Ctrl+C で止めた")

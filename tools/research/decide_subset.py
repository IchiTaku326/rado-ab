#!/usr/bin/env python3
r"""decide_subset.py -- 105 (cegar) が育てた部分集合 S' が k 色で塗れるかを、分割探索で決着させる (2026-11-03)。
S' は results/cegar/cegar_a{a}_b{b}_k{k}_n{n}.json の "S"。使う解は x, y, z が全て S' に入る a(x-y)=bz の解だけ
(全体 [1,n] の問題の一部の節なので、S' が塗れなければ [1,n] も塗れない = R_k <= n の候補。証明ファイルは別の作業)。
キューブ: S' の小さい順の先頭 D 個の first-fit の塗り方 (色の入れ替えで一般性を失わない)。各キューブを CaDiCaL (別プロセス、
--wall 秒で必ず kill) で解き、時間切れなら次の --split 個で分けた子キューブを後で解く (子も同じ、深さに上限なし)。
結果は 1 キューブごとに results/cegar/decide_a.._n...csv に追記 (flush + fsync)。止めて続きから (済んだキューブは飛ばす)。
SAT なら S' の塗り方を保存して止まる (このときは R_k <= n ではない。105 を再実行すれば cegar が続きから)。
全部 UNSAT なら「S' は塗れない」と RESULT ファイルに書く。
使い方 (WSL): python3 tools/research/decide_subset.py 3 5 4 961 --workers 11 --depth 6 --wall 600 --split 2
"""
import argparse, csv, json, os, shutil, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9)); now = lambda: datetime.now(JST).strftime("%m-%d %H:%M:%S")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ap = argparse.ArgumentParser()
for x in "abkn": ap.add_argument(x, type=int)
ap.add_argument("--workers", type=int, default=11); ap.add_argument("--depth", type=int, default=6)
ap.add_argument("--wall", type=int, default=600); ap.add_argument("--split", type=int, default=2)
ap.add_argument("--cadical", default=""); ap.add_argument("--state", default="")
ap.add_argument("--max-hours", type=float, default=0, help="stop (resumable) after this many hours; 0 = no limit")
A = ap.parse_args(); a, b, k, n = A.a, A.b, A.k, A.n
OUTD = os.path.join(ROOT, "results", "cegar"); os.makedirs(OUTD, exist_ok=True)
STF = A.state or os.path.join(OUTD, f"cegar_a{a}_b{b}_k{k}_n{n}.json")
S = sorted(json.load(open(STF))["S"])
tag = f"a{a}_b{b}_k{k}_n{n}_S{len(S)}"
LOG = os.path.join(OUTD, f"decide_{tag}.csv"); RES = os.path.join(OUTD, f"DECIDE_{tag}.txt")
cad = A.cadical or os.path.join(tempfile.gettempdir(), "ds_cadical")
if not A.cadical:
    shutil.copy(os.path.join(ROOT, "bin_linux", "cadical"), cad); os.chmod(cad, 0o755)

idx = {x: i for i, x in enumerate(S)}; v = lambda x, c: k * idx[x] + c + 1
Sset = set(S); base = [[v(x, c) for c in range(k)] for x in S]
nsol = 0
for z in range(a, n + 1, a):
    if z not in Sset or (b * z) % a: continue
    d = b * z // a
    for y in S:
        x = y + d
        if x > n: break
        if x in Sset:
            T = sorted({x, y, z}); nsol += 1
            for c in range(k): base.append([-v(t, c) for t in T])
NV = k * len(S)
fd, BASEF = tempfile.mkstemp(suffix=".cnf"); os.close(fd)
with open(BASEF, "w") as f: f.writelines(" ".join(map(str, c)) + " 0\n" for c in base)

def ff_children(prefix, m):
    """first-fit extensions of the colour prefix by m more elements"""
    out = [list(prefix)]
    for _ in range(m):
        out = [p + [c] for p in out for c in range(min(k, (max(p) + 2) if p else 1))]
    return out

PROCS = set(); PL = threading.Lock(); STOP = threading.Event()
def solve(cube):
    fd, f = tempfile.mkstemp(suffix=".cnf"); os.close(fd)
    try:
        with open(f, "w") as fh:
            fh.write(f"p cnf {NV} {len(base) + len(cube)}\n"); fh.write(open(BASEF).read())
            fh.writelines(f"{v(S[i], c)} 0\n" for i, c in enumerate(cube))
        t0 = time.time()
        p = subprocess.Popen([cad, "-q", f], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        with PL: PROCS.add(p)
        try:
            out, _ = p.communicate(timeout=A.wall)
        except subprocess.TimeoutExpired:
            p.kill(); p.communicate(); return "TIMEOUT", None, time.time() - t0
        finally:
            with PL: PROCS.discard(p)
        if p.returncode == 20: return "UNSAT", None, time.time() - t0
        if p.returncode == 10:
            val = {int(t) for l in out.splitlines() if l.startswith("v") for t in l.split()[1:] if int(t) > 0}
            return "SAT", val, time.time() - t0
        return ("CANCELLED" if STOP.is_set() else "ERROR"), None, time.time() - t0
    finally:
        os.remove(f)

key = lambda cube: "".join(map(str, cube))
done = {}
if os.path.exists(LOG):
    for r in csv.DictReader(open(LOG)): done[r["cube"]] = r["result"]
new = not os.path.exists(LOG)
fo = open(LOG, "a", newline=""); w = csv.writer(fo)
if new: w.writerow(["jst_time", "cube", "result", "seconds"])
def put(c, r, s):
    w.writerow([now(), c, r, f"{s:.1f}"]); fo.flush(); os.fsync(fo.fileno()); done[c] = r

# rebuild the open frontier: root cubes and children of TIMEOUT cubes, minus finished ones
def frontier():
    todo = []; stack = ff_children([], min(A.depth, len(S)))
    while stack:
        cu = stack.pop(); r = done.get(key(cu))
        if r in ("UNSAT",): continue
        if r == "TIMEOUT" and len(cu) < len(S):
            stack.extend(ff_children(cu, min(A.split, len(S) - len(cu)))); continue
        if r == "SAT": return None
        todo.append(cu)
    todo.sort(key=lambda cu: (len(cu), key(cu)))
    return todo

print(f"[{now()}] S' = {len(S)} 個 / n = {n}、解 {nsol} 個、{k} 色。根のキューブ: 先頭 {A.depth} 個、時間切れは次の {A.split} 個で分割。"
      f" {A.workers} 並列、1 キューブ最長 {A.wall} 秒。記録: {LOG}", flush=True)
if any(r == "SAT" for r in done.values()):
    print("既に SAT のキューブがある(S' は塗れる)。"); sys.exit(0)
t_start = time.time(); last = 0; sat = None; times = []
from collections import deque
pending = deque(frontier() or [])
retry = {}
try:
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        running = {}
        while pending or running:
            while pending and len(running) < A.workers and not sat:      # keep all workers busy
                cu = pending.popleft(); running[ex.submit(solve, cu)] = cu
            fin, _ = wait(running, timeout=30, return_when=FIRST_COMPLETED)
            for fu in fin:
                cu = running.pop(fu); r, val, sec = fu.result()
                if r in ("UNSAT", "TIMEOUT", "SAT"):
                    put(key(cu), r, sec); times.append(min(sec, A.wall))
                if r == "TIMEOUT" and len(cu) < len(S):
                    pending.extend(ff_children(cu, min(A.split, len(S) - len(cu))))   # split at once (no idle tail)
                elif r == "SAT" and sat is None:
                    sat = {x: next(c for c in range(k) if v(x, c) in val) for x in S}; STOP.set(); pending.clear()
                    with PL:
                        for p in list(PROCS): p.kill()
                elif r == "ERROR":
                    retry[key(cu)] = retry.get(key(cu), 0) + 1
                    if retry[key(cu)] <= 2: pending.append(cu)
                    else: print(f"[{now()}] キューブ {key(cu)} が 3 回エラー(飛ばさず止める)", flush=True); raise KeyboardInterrupt
            if A.max_hours and time.time() - t_start > A.max_hours * 3600:
                raise KeyboardInterrupt
            if time.time() - last > 60:
                last = time.time(); vals = list(done.values())
                mean = sum(times) / len(times) if times else float("nan")
                left = len(pending) + len(running)
                print(f"[{now()}] 済み {len(vals)} キューブ (UNSAT {vals.count('UNSAT')}, 時間切れ→分割 {vals.count('TIMEOUT')})、"
                      f"残り(今わかっている分) {left} 本、{len(running)} 本実行中、経過 {(time.time()-t_start)/60:.0f} 分、"
                      f"今の分だけなら あと約 {left*mean/A.workers/60:.0f} 分 (分割が増えると延びる)", flush=True)
except KeyboardInterrupt:
    STOP.set()
    with PL:
        for p in list(PROCS): p.kill()
    print(f"[{now()}] 止めた (Ctrl+C か --max-hours の上限)。済んだキューブは保存済み。同じコマンドで続きから。", flush=True)
    os.remove(BASEF); sys.exit(1)
if not sat:
    rest = frontier()
    if rest is None: sat = None
    elif rest:
        print(f"[{now()}] まだ {len(rest)} キューブ残っている(想定外)。同じコマンドで続きから。", flush=True); os.remove(BASEF); sys.exit(1)
os.remove(BASEF)
if sat:
    # check the colouring of S' directly
    bad = sum(1 for z in range(a, n + 1, a) if z in Sset and (b*z) % a == 0
              for y in S if y + b*z//a in Sset and sat[y] == sat[y + b*z//a] == sat[z])
    out = os.path.join(OUTD, f"decide_{tag}_colouring.json")
    json.dump({"a": a, "b": b, "k": k, "n": n, "S": S, "colouring": [sat[x] for x in S]}, open(out, "w"))
    msg = (f"R{k}({a}(x-y)={b}z), n = {n}, S' = {len(S)} 個  [{now()} JST]\n"
           f"【結果】S' は {k} 色で塗れる(単色の解 {bad} 個を直接確認)。→ この S' では上界は出ない。塗り方: {out}\n"
           f"  次: 105 をもう一度(cegar が S' を育てる)。\n")
else:
    msg = (f"R{k}({a}(x-y)={b}z), n = {n}, S' = {len(S)} 個  [{now()} JST]\n"
           f"【結果】S' は {k} 色で塗れない(全てのキューブが UNSAT、CaDiCaL の判定)。→ R{k} <= {n} の候補。\n"
           f"  証明にするには: キューブごとに LRAT を作り cake_lpr で検査 + 分け方が全部をおおうことの確認(次の作業)。\n"
           f"  キューブ数 {sum(1 for r in done.values() if r == 'UNSAT')} (UNSAT)。記録: {LOG}\n")
open(RES, "w", encoding="utf-8").write(msg); print("\n" + msg, flush=True)

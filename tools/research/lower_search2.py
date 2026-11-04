# -*- coding: utf-8 -*-
r"""lower_search2.py (2026-11-03): does a simple formula for R_k(a(x-y)=bz) break at k colours?  We look for a good
k-colouring of [1,n] at n = the formula value F (if one exists, R_k > F and the formula is wrong for this k), and then at
larger n.  Lower bounds only: "not found" is NOT an upper bound.
Method: the formula of [1,n] (all solutions, colour of 1 fixed, or with --struct 1 the numbers with v_a(x) = 1 have colour 0
and the numbers not divisible by a do not) is split into first-fit cubes of the first D free numbers; every cube is one
CaDiCaL --sat run in its own process (killed after --wall seconds, so a hanging solver cannot block the run).
The first satisfiable cube gives a colouring that is CHECKED against all solutions by a separate routine and saved as
results/lower5/cert_a{a}_b{b}_k{k}_n{n}.json; then the next n of the list is tried.
Resumable: results/lower5/progress.csv has one row per finished cube (flush + fsync); results/lower5/summary.csv one row per n.
Parallel workers, ETA every minute, Ctrl+C stops all solvers at once.
Run (inside WSL, project folder): python3 tools/research/lower_search2.py --a 4 --b 1 --k 5 --struct 1 --wall 300 1024 1040"""
import argparse, csv, json, os, signal, subprocess, sys, tempfile, time
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9)); now = lambda: datetime.now(JST).strftime("%m-%d %H:%M:%S")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
OUT = os.path.join(ROOT, "results", "lower5")
G = {}


def va(x, a):
    j = 0
    while a > 1 and x % a == 0:
        x //= a; j += 1
    return j


def solutions(a, b, n):
    s = 1
    while a * s <= n and b * s < n:
        z, d = a * s, b * s
        for y in range(1, n - d + 1):
            yield y + d, y, z
        s += 1


def base_cnf(a, b, k, n, struct, fn):
    v = lambda x, c: (x - 1) * k + c + 1
    cl = [[v(x, c) for c in range(k)] for x in range(1, n + 1)]
    if struct:
        for x in range(1, n + 1):
            j = va(x, a)
            if j == 1: cl.append([v(x, 0)])
            elif j == 0: cl.append([-v(x, 0)])
    else:
        cl.append([v(1, 0)])
    for t in solutions(a, b, n):
        T = sorted(set(t))
        for c in range(k): cl.append([-v(u, c) for u in T])
    with open(fn, "w") as f:
        f.write(f"p cnf {n * k} {len(cl)}\n"); f.write("".join(" ".join(map(str, c)) + " 0\n" for c in cl))
    return len(cl)


def cube_list(a, k, n, struct, depth):
    """first-fit colour sequences for the first `depth` free numbers (colour names are symmetric: with --struct 1 the colours
    1..k-1, otherwise 0..k-1 with the number 1 fixed to colour 0)"""
    lo = 1 if struct else 0
    xs = [x for x in range(1, n + 1) if x % a][:depth] if struct else list(range(2, n + 1))[:depth]
    out = [()]
    for _ in xs:
        out = [p + (c,) for p in out for c in range(lo, min(k - 1, (max(p) if p else 0) + 1) + 1)]
    return xs, out


def job(cube, wall):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    a, b, k, n, xs = G["a"], G["b"], G["k"], G["n"], G["xs"]
    v = lambda x, c: (x - 1) * k + c + 1
    fd, fn = tempfile.mkstemp(suffix=".cnf", dir=G["tmp"]); os.close(fd)
    t0 = time.time(); col = None
    try:
        with open(G["base"]) as src, open(fn, "w") as f:
            head = src.readline().split()
            f.write(f"p cnf {head[2]} {int(head[3]) + len(cube)}\n")
            for line in src: f.write(line)
            for x, c in zip(xs, cube): f.write(f"{v(x, c)} 0\n")
        p = subprocess.Popen([G["cad"], "-q", "--sat", fn], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                             start_new_session=True)
        pidf = os.path.join(G["tmp"], f"pid_{p.pid}"); open(pidf, "w").close()
        try:
            out, _ = p.communicate(timeout=wall); rc = p.returncode
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL); p.communicate(); rc = 0; out = ""
        try: os.unlink(pidf)
        except OSError: pass
        res = {10: "SAT", 20: "UNSAT"}.get(rc, "TIMEOUT")
        if res == "SAT":
            pos = {int(z) for l in out.splitlines() if l.startswith("v") for z in l.split()[1:] if int(z) > 0}
            col = [next(c for c in range(k) if v(x, c) in pos) for x in range(1, n + 1)]
    finally:
        os.unlink(fn)
    return cube, res, round(time.time() - t0, 1), col


def init(d):
    G.update(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, required=True); ap.add_argument("--b", type=int, required=True); ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--struct", type=int, default=0); ap.add_argument("--depth", type=int, default=6)
    ap.add_argument("--workers", type=int, default=11); ap.add_argument("--wall", type=int, default=300)
    ap.add_argument("--cadical", default=os.path.join(ROOT, "bin_linux", "cadical"))
    ap.add_argument("ns", type=int, nargs="+"); A = ap.parse_args()
    if A.struct and A.a < 2: sys.exit("--struct 1 needs a >= 2")
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(tempfile.gettempdir(), f"lower5_{A.a}_{A.b}_{A.k}"); os.makedirs(tmp, exist_ok=True)
    cad = os.path.join(tmp, "cadical")
    import shutil; shutil.copy(A.cadical, cad); os.chmod(cad, 0o755)
    sumf = os.path.join(OUT, "summary.csv"); progf = os.path.join(OUT, "progress.csv")
    done_n = {}
    if os.path.exists(sumf):
        for r in csv.DictReader(open(sumf, encoding="utf-8")):
            if (int(r["a"]), int(r["b"]), int(r["k"]), int(r["struct"])) == (A.a, A.b, A.k, A.struct): done_n[int(r["n"])] = r["result"]
    for fn_, hdr in ((sumf, ["jst_time", "a", "b", "k", "struct", "n", "result", "cubes_done", "cubes_total"]),
                     (progf, ["jst_time", "a", "b", "k", "struct", "n", "cube", "result", "seconds"])):
        if not os.path.exists(fn_): open(fn_, "w", encoding="utf-8").write(",".join(hdr) + "\n")
    fs = open(sumf, "a", newline="", encoding="utf-8"); ws = csv.writer(fs)
    fp = open(progf, "a", newline="", encoding="utf-8"); wp = csv.writer(fp)
    tag = f"R{A.k}({A.a}(x-y)={A.b}z){' struct' if A.struct else ''}"
    for n in A.ns:
        if n in done_n:
            print(f"[{now()}] {tag} n={n}: already {done_n[n]}", flush=True)
            if done_n[n] != "FOUND": break
            continue
        fin = set()
        for r in csv.DictReader(open(progf, encoding="utf-8")):
            if (int(r["a"]), int(r["b"]), int(r["k"]), int(r["struct"]), int(r["n"])) == (A.a, A.b, A.k, A.struct, n): fin.add(r["cube"])
        base = os.path.join(tmp, f"base_{n}.cnf"); ncl = base_cnf(A.a, A.b, A.k, n, A.struct, base)
        xs, cubes = cube_list(A.a, A.k, n, A.struct, A.depth)
        names = {c: "".join(map(str, c)) for c in cubes}
        todo = [c for c in cubes if names[c] not in fin]
        print(f"[{now()}] {tag} n={n}: {ncl} clauses, {len(cubes)} cubes ({len(cubes) - len(todo)} done earlier), "
              f"{A.workers} workers, {A.wall} s per cube", flush=True)
        ex = ProcessPoolExecutor(A.workers, initializer=init,
                                 initargs=(dict(a=A.a, b=A.b, k=A.k, n=n, xs=xs, base=base, cad=cad, tmp=tmp),))
        running = {}; found = None; t0 = time.time(); cnt = 0; spent = 0.0; last = time.time()
        try:
            while (todo or running) and not found:
                while todo and len(running) < A.workers:
                    c = todo.pop(0); running[ex.submit(job, c, A.wall)] = c
                fin_f, _ = wait(list(running), timeout=60, return_when=FIRST_COMPLETED)
                for f in fin_f:
                    cube, res, sec, col = f.result(); del running[f]; cnt += 1; spent += sec
                    if res == "SAT":
                        C = [None] + col
                        bad = sum(1 for (x, y, z) in solutions(A.a, A.b, n) if C[x] == C[y] == C[z])
                        if bad == 0: found = (cube, col); break
                        print(f"[{now()}] WARNING: cube {names[cube]} SAT but the check found {bad} monochromatic solutions", flush=True)
                        res = "SAT_CHECK_FAILED"
                    wp.writerow([now(), A.a, A.b, A.k, A.struct, n, names[cube], res, sec]); fp.flush(); os.fsync(fp.fileno())
                if time.time() - last > 60:
                    last = time.time(); left = len(todo) + len(running)
                    print(f"[{now()}]   n={n}: {cnt} cubes done in this run, none colourable yet; {left} left; "
                          f"at most ~{spent / max(cnt, 1) * left / A.workers / 60:.0f} min more (rough)", flush=True)
        except KeyboardInterrupt:
            print("stopping (Ctrl+C) ...", flush=True)
            for pf in os.listdir(tmp):
                if pf.startswith("pid_"):
                    try: os.killpg(int(pf[4:]), signal.SIGKILL)
                    except Exception: pass
                    try: os.unlink(os.path.join(tmp, pf))
                    except OSError: pass
            for pr in list(getattr(ex, "_processes", {}).values()):
                try: pr.kill()
                except Exception: pass
            fp.close(); fs.close()
            print("stopped. Finished cubes are saved; the same command continues.", flush=True); os._exit(1)
        for pf in os.listdir(tmp):                               # a find stops the other cubes of this n
            if pf.startswith("pid_"):
                try: os.killpg(int(pf[4:]), signal.SIGKILL)
                except Exception: pass
                try: os.unlink(os.path.join(tmp, pf))
                except OSError: pass
        ex.shutdown(wait=True, cancel_futures=True)
        if found:
            cube, col = found
            json.dump({"a": A.a, "b": A.b, "k": A.k, "n": n, "coloring": col, "cube": names[cube], "struct": A.struct,
                       "checked": "all solutions (lower_search2.py)"},
                      open(os.path.join(OUT, f"cert_a{A.a}_b{A.b}_k{A.k}_n{n}.json"), "w"))
            ws.writerow([now(), A.a, A.b, A.k, A.struct, n, "FOUND", cnt, len(cubes)]); fs.flush(); os.fsync(fs.fileno())
            msg = f"[{now()}] {tag} n={n}: GOOD COLOURING FOUND and checked -> R{A.k} > {n}"
            print(msg, flush=True); open(os.path.join(OUT, "FOUND.txt"), "a", encoding="utf-8").write(msg + "\n")
        else:
            ws.writerow([now(), A.a, A.b, A.k, A.struct, n, "NOT_FOUND", cnt, len(cubes)]); fs.flush(); os.fsync(fs.fileno())
            print(f"[{now()}] {tag} n={n}: no colouring found within the limits (NOT an upper bound) -> stop this list", flush=True)
            break
    print(f"[{now()}] {tag}: done (results/lower5/)", flush=True)


if __name__ == "__main__":
    main()

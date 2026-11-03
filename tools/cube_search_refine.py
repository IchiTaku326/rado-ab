# -*- coding: utf-8 -*-
r"""
Cube search for R_k(a(x-y)=bz) at one n: split on the colours of 1..d (canonical = first-fit symmetry)
and solve every cube with a conflict budget.  Used to find out whether n is UNSAT (R = n) or to find a colouring.

  * resumable: each worker appends one row per finished cube to its own CSV (flush+fsync, JST time);
    on restart finished cubes (SAT/UNSAT) are skipped, UNKNOWN cubes are retried with a 4x larger budget.
  * backend pysat : one Glucose4 solver per worker with assumptions (learned clauses are kept between cubes)
  * backend cadical : the cadical binary per cube (--conflicts=N); the same code path can add DRAT proofs later.
  * SAT -> colouring saved as JSON and checked by rado_verify.py.

PowerShell:  python tools\cube_search.py --a 2 --b 3 --k 4 --n 226 --depth 10 --workers 11 --backend pysat --outdir results\cube226
"""
import argparse, csv, json, os, subprocess, sys, tempfile, time
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rado_c1 import build_cnf, solutions, write_dimacs

JST = timezone(timedelta(hours=9))
FIELDS = ["jst_time", "cube", "status", "budget", "conflicts", "seconds", "worker", "note"]


def now():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")


def enum_cubes(a, b, k, d):
    """canonical colourings (restricted growth strings) of 1..d with no monochromatic solution inside 1..d"""
    sols = [tuple(sorted(s)) for s in solutions(a, b, d)]
    by_max = {}
    for s in sols:
        by_max.setdefault(s[-1], []).append(s)
    out = []
    col = [0] * (d + 1)

    def rec(j, used):
        if j > d:
            out.append(tuple(col[1:]))
            return
        for c in range(min(used + 1, k)):
            col[j] = c
            if all(not (col[s[0]] == col[s[1]] == col[s[2]]) if len(s) == 3 else
                   not all(col[t] == c for t in s) for s in by_max.get(j, [])):
                rec(j + 1, max(used, c + 1))
    rec(1, 0)
    return out


def extend_cubes(a, b, k, parents, extra):
    """children of the given parent prefixes: colour the next `extra` numbers (canonical, no monochromatic solution)"""
    d0 = len(parents[0]) if parents else 0
    d = d0 + extra
    by_max = {}
    for sol in solutions(a, b, d):
        t = tuple(sorted(sol))
        by_max.setdefault(t[-1], []).append(t)
    out = []
    for pc in parents:
        col = [0] + list(pc) + [0] * extra

        def rec(j, used):
            if j > d:
                out.append(tuple(col[1:]))
                return
            for c in range(min(used + 1, k)):
                col[j] = c
                if all(not all(col[t] == c for t in sol) for sol in by_max.get(j, [])):
                    rec(j + 1, max(used, c + 1))
        rec(d0 + 1, max(pc) + 1 if pc else 0)
    return out


def get_cubes(args):
    base = enum_cubes(args.a, args.b, args.k, args.depth)
    if getattr(args, "refine_of", None):
        done, unk = done_cubes(args.refine_of)
        parents = [base[i] for i in range(len(base)) if i not in done]
        return extend_cubes(args.a, args.b, args.k, parents, args.extra)
    return base


def done_cubes(outdir):
    done, unk = {}, {}
    for fn in os.listdir(outdir):
        if fn.startswith("cubes_w") and fn.endswith(".csv"):
            with open(os.path.join(outdir, fn), newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    c = int(r["cube"])
                    if r["status"] in ("SAT", "UNSAT"):
                        done[c] = r["status"]
                    elif r["status"] == "UNKNOWN":
                        unk[c] = max(unk.get(c, 0), int(r["budget"]))
    return done, unk


def worker(args, w):
    a, b, k, n, d = args.a, args.b, args.k, args.n, args.depth
    cubes = get_cubes(args)
    cl, nvars, v = build_cnf(a, b, k, n)
    path = os.path.join(args.outdir, f"cubes_w{w}.csv")
    new = not os.path.exists(path)
    fh = open(path, "a", newline="", encoding="utf-8")
    wr = csv.DictWriter(fh, fieldnames=FIELDS)
    if new:
        wr.writeheader(); fh.flush(); os.fsync(fh.fileno())
    S = None
    since_new = 0
    if args.backend == "pysat":
        from pysat.solvers import Glucose4
        S = Glucose4(bootstrap_with=cl)
    mine = [i for i in range(len(cubes)) if i % args.workers == w]
    while True:
        done, unk = done_cubes(args.outdir)
        todo = [i for i in mine if i not in done]
        if not todo:
            return
        progressed = False
        for i in todo:
            budget = args.budget if i not in unk else unk[i] * 4
            if i in unk and unk[i] >= args.max_budget:
                continue
            progressed = True
            assum = [v(j + 1, c) for j, c in enumerate(cubes[i])]
            t0 = time.time(); model = None; note = ""
            if S is not None:
                since_new += 1
                if since_new > 300:          # keep memory bounded: fresh solver every 300 cubes
                    S.delete(); S = Glucose4(bootstrap_with=cl); since_new = 0
                S.conf_budget(budget)
                r = S.solve_limited(assumptions=assum)
                st = "SAT" if r is True else "UNSAT" if r is False else "UNKNOWN"
                if r is True:
                    model = {abs(l): l > 0 for l in S.get_model()}
            else:
                fd, tmp = tempfile.mkstemp(suffix=".cnf"); os.close(fd)
                try:
                    write_dimacs(tmp, cl + [[x] for x in assum], nvars)
                    p = subprocess.run([args.bin, "-q", "-c", str(budget), tmp], capture_output=True, text=True)
                    st = "UNKNOWN"
                    if p.returncode not in (0, 10, 20):
                        raise RuntimeError("solver failed: " + p.stderr[:200])
                    mm = {}
                    for line in p.stdout.splitlines():
                        if line.startswith("s SATISFIABLE"): st = "SAT"
                        elif line.startswith("s UNSATISFIABLE"): st = "UNSAT"
                        elif line.startswith("v "):
                            for tok in line[2:].split():
                                t = int(tok)
                                if t: mm[abs(t)] = t > 0
                    if st == "SAT": model = mm
                finally:
                    os.remove(tmp)
            wr.writerow({"jst_time": now(), "cube": i, "status": st, "budget": budget, "conflicts": "",
                         "seconds": round(time.time() - t0, 2), "worker": w, "note": note})
            fh.flush(); os.fsync(fh.fileno())
            if st == "SAT":
                col = [next(c for c in range(k) if model.get(v(j, c), False)) for j in range(1, n + 1)]
                cert = os.path.join(args.outdir, f"cert_a{a}_b{b}_k{k}_n{n}_cube{i}.json")
                with open(cert, "w", encoding="utf-8") as f:
                    json.dump({"a": a, "b": b, "k": k, "n": n, "jst_time": now(), "coloring": col}, f)
                    f.flush(); os.fsync(f.fileno())
                vp = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "rado_verify.py"), cert],
                                    capture_output=True, text=True)
                print(f"[{now()} JST] SAT cube {i}: verify={'ok' if vp.returncode == 0 else 'FAILED'} {cert}", flush=True)
                return
        if not progressed:
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, default=2); ap.add_argument("--b", type=int, default=3)
    ap.add_argument("--k", type=int, default=4); ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--depth", type=int, default=10)
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--backend", choices=["pysat", "cadical"], default="pysat")
    ap.add_argument("--bin", default="cadical")
    ap.add_argument("--budget", type=int, default=20000, help="conflicts per cube in the first pass")
    ap.add_argument("--max-budget", type=int, default=10**9)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--worker-id", type=int, default=None, help="internal")
    ap.add_argument("--refine-of", default=None, help="dir of a finished/stopped run: split its still-open cubes further")
    ap.add_argument("--extra", type=int, default=4, help="with --refine-of: how many more numbers to colour")
    ap.add_argument("--log-minutes", type=float, default=5)
    ap.add_argument("--report", action="store_true", help="only print progress")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    cubes = get_cubes(args)
    if args.report:
        done, unk = done_cubes(args.outdir)
        nu = sum(1 for s in done.values() if s == "UNSAT"); ns = sum(1 for s in done.values() if s == "SAT")
        print(f"[{now()} JST] cubes={len(cubes)} UNSAT={nu} SAT={ns} UNKNOWN(open)={len([c for c in unk if c not in done])} untouched={len(cubes) - len(done) - len([c for c in unk if c not in done])}")
        return
    if args.worker_id is not None:
        worker(args, args.worker_id); return
    keep_awake()
    print(f"[{now()} JST] n={args.n} depth={args.depth}: {len(cubes)} cubes, {args.workers} workers", flush=True)
    plog = os.path.join(args.outdir, "progress.log")

    def spawn(w):
        cmd = [sys.executable, os.path.abspath(__file__)] + [x for x in sys.argv[1:]] + ["--worker-id", str(w)]
        return subprocess.Popen(cmd)

    def kill_all(ps):
        for p in ps.values():
            if p.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.kill()

    def have_cert():
        return any(f.startswith("cert_") and f.endswith(".json") for f in os.listdir(args.outdir))

    def log_progress():
        done, unk = done_cubes(args.outdir)
        nu = sum(1 for x in done.values() if x == "UNSAT"); ns = sum(1 for x in done.values() if x == "SAT")
        op = len([c for c in unk if c not in done])
        line = f"[{now()} JST] cubes={len(cubes)} UNSAT={nu} SAT={ns} open_unknown={op} untouched={len(cubes)-len(done)-op}"
        print(line, flush=True)
        with open(plog, "a", encoding="utf-8") as f:
            f.write(line + "\n"); f.flush(); os.fsync(f.fileno())
        return nu, ns

    ps = {w: spawn(w) for w in range(args.workers)}
    finished = set()
    last_log = 0
    try:
        while len(finished) < args.workers:
            time.sleep(5)
            for w, p in list(ps.items()):
                rc = p.poll()
                if rc is None or w in finished:
                    continue
                if rc == 0:
                    finished.add(w)
                else:
                    print(f"[{now()} JST] worker {w} died (rc={rc}); restarting in 10 s", flush=True)
                    time.sleep(10)
                    ps[w] = spawn(w)
            if have_cert():
                print(f"[{now()} JST] a colouring was found -> stopping all workers", flush=True)
                kill_all(ps); break
            if time.time() - last_log > args.log_minutes * 60:
                log_progress(); last_log = time.time()
    except KeyboardInterrupt:
        kill_all(ps)
        print("\n[interrupted] finished cubes are kept; run again to resume")
        return
    nu, ns = log_progress()
    with open(os.path.join(args.outdir, "FINAL.txt"), "a", encoding="utf-8") as f:
        f.write(f"[{now()} JST] n={args.n} depth={args.depth} cubes={len(cubes)} UNSAT={nu} SAT={ns} "
                f"all_unsat={'YES' if nu == len(cubes) else 'no'}\n")


def keep_awake():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        except Exception:
            pass


if __name__ == "__main__":
    main()

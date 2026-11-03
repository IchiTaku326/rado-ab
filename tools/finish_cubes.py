# -*- coding: utf-8 -*-
r"""
Finish the last (very hard) cubes of a cube_search run.

Why: cube_search.py solves each cube with Glucose4 + conf_budget(20000).  For a few cubes Glucose does not stop at
the budget (Glucose checks the budget only between restarts; when restarts are blocked it keeps going), so the
"budget -> UNKNOWN -> split" mechanism never fires and the run waits for days at 99%.
(a5_b3_k4_n625: 9 cubes running 18-50 h each, while a normal cube takes ~70 s.)

What this does (no budget, a hard wall-clock limit instead):
  * takes the still-open top cubes of <cube dir> (same read_state as cube_search.py),
  * solves each in its OWN process with a pysat solver (default cadical153, no conflict budget),
  * the parent KILLS the process after --timeout seconds -> the cube is split (colour --extra more numbers)
    and the children are solved the same way (recursively),
  * every result is one row in <cube dir>\finish.csv (flush+fsync, JST time) -> Ctrl+C is safe; on restart the
    finished parts are skipped (only the solves that were running are lost),
  * a top cube whose whole subtree is UNSAT gets one row  "cube,UNSAT,...,note=finish"  in
    <cube dir>\cubes_wfinish.csv, so cube_search.py / grid_rado.py see it as done,
  * SAT -> colouring saved as cert_*.json, checked by rado_verify.py, SAT row written, everything stops.

The CNF is the same as in the run (build_cnf with --implied, first-fit symmetry breaking, same cube enumeration),
so the results are interchangeable with cube_search.py rows.  STOP the grid_rado / cube_search run first.

PowerShell:
  python tools\finish_cubes.py --a 5 --b 3 --k 4 --n 625 --implied 1 --outdir D:\sat_work\cubes\a5_b3_k4_n625
"""
import argparse, csv, json, os, subprocess, sys, time
import multiprocessing as mp
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
JST = timezone(timedelta(hours=9))
FFIELDS = ["jst_time", "prefix", "status", "seconds", "solver", "note"]
CFIELDS = ["jst_time", "cube", "status", "budget", "conflicts", "seconds", "worker", "note"]


def now():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")


def enc(prefix):
    return "".join(str(c) for c in prefix)


def dec(s):
    return tuple(int(ch) for ch in s)


# ---------------------------------------------------------------- child process: build CNF, solve one prefix
def _solve_task(a, b, k, n, implied, solver, prefix, conn):
    try:
        from rado_c1 import build_cnf
        from pysat.solvers import Solver
        cl, nvars, v = build_cnf(a, b, k, n, implied=implied)
        t0 = time.time()
        with Solver(name=solver, bootstrap_with=cl) as S:
            r = S.solve(assumptions=[v(j + 1, c) for j, c in enumerate(prefix)])
            col = None
            if r:
                m = set(l for l in S.get_model() if l > 0)
                col = [next(c for c in range(k) if v(j, c) in m) for j in range(1, n + 1)]
        conn.send(("SAT" if r else "UNSAT", time.time() - t0, col))
    except Exception as e:                                    # report, never hang
        conn.send(("ERROR", 0.0, repr(e)))
    finally:
        conn.close()


# ---------------------------------------------------------------- state
def read_finish(path):
    done, split = {}, {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                p = r["prefix"]
                if r["status"] in ("SAT", "UNSAT"):
                    done[p] = r["status"]
                elif r["status"] == "SPLIT":
                    split[p] = int(r["note"].split("=")[1])
    return done, split


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, required=True); ap.add_argument("--b", type=int, required=True)
    ap.add_argument("--k", type=int, required=True); ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--depth", type=int, default=10, help="cube depth of the original run (must match)")
    ap.add_argument("--implied", type=int, default=1, help="must match the original run (24_run_implied.bat: 1)")
    ap.add_argument("--outdir", required=True, help="the cube folder of the run, e.g. D:\\sat_work\\cubes\\a5_b3_k4_n625")
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--solver", default="cadical153", help="pysat solver name (cadical153, glucose4, maplechrono, ...)")
    ap.add_argument("--timeout", type=float, default=4 * 3600, help="wall-clock seconds per solve; then split")
    ap.add_argument("--extra", type=int, default=2, help="numbers coloured more when a cube is split")
    ap.add_argument("--cubes", default="", help="only these top cubes (comma list); default = all open ones")
    ap.add_argument("--log-seconds", type=float, default=600)
    args = ap.parse_args()

    from cube_search import enum_cubes, extend_cubes, read_state
    a, b, k, n = args.a, args.b, args.k, args.n
    base = enum_cubes(a, b, k, args.depth)
    done0, _u, _s, _cd, _cu = read_state(args.outdir)
    if any(st == "SAT" for st in done0.values()):
        print("a cube of this run is already SAT -> nothing to do"); return
    tops = [int(x) for x in args.cubes.split(",") if x.strip()] if args.cubes else \
           [i for i in range(len(base)) if i not in done0]
    tops = [i for i in tops if i not in done0]
    print(f"[{now()} JST] {a=} {b=} {k=} {n=} cubes={len(base)} open top cubes={len(tops)}: {tops}", flush=True)
    if not tops:
        print("all cubes are finished"); return

    fpath = os.path.join(args.outdir, "finish.csv")
    new = not os.path.exists(fpath)
    fh = open(fpath, "a", newline="", encoding="utf-8")
    fw = csv.DictWriter(fh, fieldnames=FFIELDS)
    if new:
        fw.writeheader()
    cpath = os.path.join(args.outdir, "cubes_wfinish.csv")
    cnew = not os.path.exists(cpath)
    ch = open(cpath, "a", newline="", encoding="utf-8")
    cw = csv.DictWriter(ch, fieldnames=CFIELDS)
    if cnew:
        cw.writeheader()
    for h in (fh, ch):
        h.flush(); os.fsync(h.fileno())
    logp = os.path.join(args.outdir, "finish_progress.log")

    def frow(prefix, st, secs, note=""):
        fw.writerow({"jst_time": now(), "prefix": enc(prefix), "status": st, "seconds": round(secs, 1),
                     "solver": args.solver, "note": note})
        fh.flush(); os.fsync(fh.fileno())

    done, split = read_finish(fpath)
    kidcache = {}

    def kids(prefix):
        key = enc(prefix)
        if key not in kidcache:
            kidcache[key] = extend_cubes(a, b, k, [prefix], args.extra)
        return kidcache[key]

    def leaves(prefix):
        """open leaves of the subtree of prefix (finished parts skipped)"""
        key = enc(prefix)
        if key in done:
            return []
        if key in split:
            out = []
            for c in kids(prefix):
                out += leaves(c)
            return out
        return [prefix]

    def subtree_sat(prefix):
        key = enc(prefix)
        if done.get(key) == "SAT":
            return True
        return key in split and any(subtree_sat(c) for c in kids(prefix))

    top_done = set()

    def check_tops():
        for i in tops:
            if i in top_done:
                continue
            if not leaves(base[i]) and not subtree_sat(base[i]):
                cw.writerow({"jst_time": now(), "cube": i, "status": "UNSAT", "budget": 0, "conflicts": "",
                             "seconds": 0, "worker": "finish", "note": "finish"})
                ch.flush(); os.fsync(ch.fileno())
                top_done.add(i)
                print(f"[{now()} JST] top cube {i}: all UNSAT  ({len(top_done)}/{len(tops)})", flush=True)

    check_tops()
    queue = []
    for i in tops:
        queue += leaves(base[i])
    ctx = mp.get_context("spawn")
    running = {}                       # key -> (proc, conn, t0, prefix)
    last_log = 0.0
    try:
        while queue or running:
            while queue and len(running) < args.workers:
                p = queue.pop(0)
                if enc(p) in done:
                    continue
                r_, w_ = ctx.Pipe(duplex=False)
                pr = ctx.Process(target=_solve_task, args=(a, b, k, n, args.implied, args.solver, p, w_), daemon=True)
                pr.start(); w_.close()
                running[enc(p)] = (pr, r_, time.time(), p)
            time.sleep(1.0)
            for key in list(running):
                pr, r_, t0, p = running[key]
                res = None
                if r_.poll():
                    try:
                        res = r_.recv()
                    except EOFError:
                        res = ("ERROR", 0.0, "child died")
                elif not pr.is_alive():
                    res = ("ERROR", 0.0, f"child exit {pr.exitcode}")
                elif time.time() - t0 > args.timeout:
                    pr.kill(); pr.join(5)
                    frow(p, "TIMEOUT", time.time() - t0)
                    ks = kids(p)
                    frow(p, "SPLIT", 0, f"children={len(ks)}")
                    split[key] = len(ks)
                    queue = ks + queue                       # children next (depth first: finishes one cube sooner)
                    print(f"[{now()} JST] timeout {key} after {time.time()-t0:.0f}s -> {len(ks)} children", flush=True)
                    del running[key]
                    check_tops()
                    continue
                if res is None:
                    continue
                pr.join(5); del running[key]
                st, secs, extra = res
                if st == "ERROR":
                    print(f"[{now()} JST] ERROR on {key}: {extra}  (retried later)", flush=True)
                    queue.append(p); time.sleep(5); continue
                frow(p, st, secs)
                done[key] = st
                print(f"[{now()} JST] {key}: {st} {secs:.0f}s", flush=True)
                if st == "SAT":
                    top = next(i for i in tops if enc(p).startswith(enc(base[i])))
                    cert = os.path.join(args.outdir, f"cert_a{a}_b{b}_k{k}_n{n}_cube{top}_finish.json")
                    with open(cert, "w", encoding="utf-8") as f:
                        json.dump({"a": a, "b": b, "k": k, "n": n, "jst_time": now(), "coloring": extra}, f)
                        f.flush(); os.fsync(f.fileno())
                    vp = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                      "rado_verify.py"), cert], capture_output=True, text=True)
                    ok = vp.returncode == 0
                    print(f"[{now()} JST] SAT! cube {top}: verify={'ok' if ok else 'FAILED'} {cert}", flush=True)
                    if ok:
                        cw.writerow({"jst_time": now(), "cube": top, "status": "SAT", "budget": 0, "conflicts": "",
                                     "seconds": round(secs, 1), "worker": "finish", "note": "finish"})
                        ch.flush(); os.fsync(ch.fileno())
                    for key2, (pr2, *_r) in running.items():
                        pr2.kill()
                    return
                check_tops()
            if time.time() - last_log > args.log_seconds:
                last_log = time.time()
                lines = [f"[{now()} JST] finish: top cubes {len(top_done)}/{len(tops)} done, running {len(running)}, queued {len(queue)}"]
                for key, (pr, r_, t0, p) in sorted(running.items()):
                    lines.append(f"    {key}: {(time.time()-t0)/3600:.2f} h")
                txt = "\n".join(lines)
                print(txt, flush=True)
                with open(logp, "a", encoding="utf-8") as lf:
                    lf.write(txt + "\n")
    except KeyboardInterrupt:
        print(f"[{now()} JST] Ctrl+C: stopping (finished results are saved; running solves are lost)", flush=True)
        for key, (pr, *_r) in running.items():
            pr.kill()
        return
    check_tops()
    print(f"[{now()} JST] done: {len(top_done)}/{len(tops)} top cubes UNSAT", flush=True)


if __name__ == "__main__":
    main()

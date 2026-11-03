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
import argparse, csv, json, os, random, shutil, subprocess, sys, tempfile, time
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


def read_state(outdir):
    """-> done{cube:status}, unk{cube:budget}, split{cube:nchildren}, cdone{(cube,j):status}, cunk{(cube,j):budget}"""
    done, unk, split, cdone, cunk = {}, {}, {}, {}, {}
    for fn in os.listdir(outdir):
        if fn.startswith("cubes_w") and fn.endswith(".csv"):
            with open(os.path.join(outdir, fn), newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    c = int(r["cube"]); note = r.get("note") or ""
                    if r["status"] == "SPLIT":
                        split[c] = int(note.split("=")[1]); continue
                    if note.startswith("child:"):
                        key = (c, int(note.split(":")[1]))
                        if r["status"] in ("SAT", "UNSAT"): cdone[key] = r["status"]
                        elif r["status"] == "UNKNOWN": cunk[key] = max(cunk.get(key, 0), int(r["budget"]))
                        continue
                    if r["status"] in ("SAT", "UNSAT"):
                        done[c] = r["status"]
                    elif r["status"] == "UNKNOWN":
                        unk[c] = max(unk.get(c, 0), int(r["budget"]))
    for c, n in split.items():          # a split cube is finished when all its children are finished
        if c in done: continue
        sts = [cdone.get((c, j)) for j in range(n)]
        if any(x == "SAT" for x in sts): done[c] = "SAT"
        elif all(x == "UNSAT" for x in sts): done[c] = "UNSAT"
    return done, unk, split, cdone, cunk


def done_cubes(outdir):
    done, unk, _s, _cd, _cu = read_state(outdir)
    return done, unk


def read_walled(outdir):
    """keys of cubes/children with a WALL row (Glucose ignored the wall-clock limit there)"""
    out = set()
    for fn in os.listdir(outdir):
        if fn.startswith("cubes_w") and fn.endswith(".csv"):
            with open(os.path.join(outdir, fn), newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r["status"] != "WALL": continue
                    note = r.get("note") or ""
                    out.add(("c", int(r["cube"]), int(note.split(":")[1])) if note.startswith("child:") else ("t", int(r["cube"])))
    return out


def worker(args, w):
    a, b, k, n, d = args.a, args.b, args.k, args.n, args.depth
    cubes = get_cubes(args)
    cl, nvars, v = build_cnf(a, b, k, n, implied=int(args.implied))
    path = os.path.join(args.outdir, f"cubes_w{w}.csv")
    new = not os.path.exists(path)
    fh = open(path, "a", newline="", encoding="utf-8")
    wr = csv.DictWriter(fh, fieldnames=FIELDS)
    if new:
        wr.writeheader(); fh.flush(); os.fsync(fh.fileno())
    st_ = {"S": None, "since_new": 0, "last_sync": time.time()}
    if args.backend == "pysat":
        from pysat.solvers import Glucose4
        st_["S"] = Glucose4(bootstrap_with=cl)

    walled = read_walled(args.outdir)       # cubes / children that once exceeded the wall-clock limit in Glucose

    def solve_cadical(assum):
        """CaDiCaL without any budget (the 9 cubes that Glucose could not finish in 18-50 h took 2-7 min here)"""
        from pysat.solvers import Cadical153
        with Cadical153(bootstrap_with=cl) as C:
            r = C.solve(assumptions=assum)
            return ("SAT" if r else "UNSAT"), ({abs(l): l > 0 for l in C.get_model()} if r else None)

    def solve(prefix, budget, key=None, i=None, note=""):
        """-> status, model, seconds.  key = ('t', i) for a cube, ('c', i, j) for a child"""
        assum = [v(j + 1, c) for j, c in enumerate(prefix)]
        t0 = time.time(); model = None
        if st_["S"] is not None and key is not None and key in walled:
            st, model = solve_cadical(assum)
            return st, model, time.time() - t0
        if st_["S"] is not None:
            st_["since_new"] += 1
            if st_["since_new"] > 300:          # keep memory bounded: fresh solver every 300 calls
                st_["S"].delete(); st_["S"] = Glucose4(bootstrap_with=cl); st_["since_new"] = 0
            S = st_["S"]
            S.conf_budget(budget)
            # WATCHDOG (2026-10-26): Glucose checks conf_budget (and interrupt) only at restarts and can run for days
            # (a5_b3_k4_n625: 9 cubes, 18-50 h).  After --wall seconds: interrupt(); if the call still has not returned
            # 60 s later, write a WALL row and end this worker process (the main process restarts it; the item is then
            # solved with CaDiCaL, see solve_cadical).
            import threading
            done_ev = threading.Event()
            def dog():
                if done_ev.wait(args.wall): return
                try: S.interrupt()
                except Exception: pass
                if done_ev.wait(60): return
                try:
                    write(i, "WALL", budget, time.time() - t0, note)
                    fh.flush(); os.fsync(fh.fileno())
                finally:
                    print(f"[{now()} JST] worker {w}: {key} exceeded {args.wall:.0f}s and ignored interrupt -> restart, then CaDiCaL", flush=True)
                    os._exit(3)
            th = threading.Thread(target=dog, daemon=True) if args.wall > 0 else None
            if th: th.start()
            try:
                r = S.solve_limited(assumptions=assum, expect_interrupt=True)
            finally:
                done_ev.set()
                try: S.clear_interrupt()
                except Exception: pass
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
        return st, model, time.time() - t0

    def write(i, st, budget, secs, note=""):
        wr.writerow({"jst_time": now(), "cube": i, "status": st, "budget": budget, "conflicts": "",
                     "seconds": round(secs, 2), "worker": w, "note": note})
        fh.flush()                                       # to the OS at once (survives Ctrl+C / kill of the program)
        if st in ("SAT", "SPLIT") or time.time() - st_["last_sync"] > 15:   # force to the disk every 15 s only (HDD)
            os.fsync(fh.fileno()); st_["last_sync"] = time.time()

    def found(i, prefix, model):
        col = [next(c for c in range(k) if model.get(v(j, c), False)) for j in range(1, n + 1)]
        cert = os.path.join(args.outdir, f"cert_a{a}_b{b}_k{k}_n{n}_cube{i}.json")
        with open(cert, "w", encoding="utf-8") as f:
            json.dump({"a": a, "b": b, "k": k, "n": n, "jst_time": now(), "coloring": col}, f)
            f.flush(); os.fsync(f.fileno())
        vp = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "rado_verify.py"), cert],
                            capture_output=True, text=True)
        print(f"[{now()} JST] SAT cube {i}: verify={'ok' if vp.returncode == 0 else 'FAILED'} {cert}", flush=True)

    cdir = os.path.join(args.outdir, "claims")
    os.makedirs(cdir, exist_ok=True)

    def claim(key):
        """work-stealing: whoever creates the claim file first (O_EXCL) solves that item; a restarted worker with the same id re-takes its own claims"""
        p = os.path.join(cdir, key)
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(w).encode()); os.close(fd)
            return True
        except FileExistsError:
            try:
                with open(p) as f: return f.read().strip() == str(w)
            except OSError:
                return False

    def late():
        return bool(getattr(args, "deadline_epoch", None)) and time.time() > args.deadline_epoch

    def do_children(i, nch, kids):
        """solve the not yet finished (and not claimed by another worker) children of split cube i; True if a colouring was found"""
        while True:
            _d, _u, _s, cdone, cunk = read_state(args.outdir)
            todo = [j for j in range(nch) if (i, j) not in cdone]
            if not todo: return False
            prog = False
            for j in todo:
                if late(): return False
                bud = args.budget if (i, j) not in cunk else cunk[(i, j)] * 4
                if (i, j) in cunk and cunk[(i, j)] >= args.max_budget: continue
                if not claim(f"c{i}_{j}"): continue
                prog = True
                st, model, secs = solve(kids[j], bud, ('c', i, j), i, f"child:{j}")
                write(i, st, bud, secs, f"child:{j}")
                if st == "SAT":
                    found(i, kids[j], model); return True
            if not prog: return False

    def handle(i):
        """work on cube i (claims it first). -> (found_colouring, progressed)"""
        done, unk, split, cdone, cunk = read_state(args.outdir)
        if i in done: return False, False
        if not claim(f"c{i}"): return False, False
        if i in split:                                   # already split: continue with its children
            kids = extend_cubes(a, b, k, [cubes[i]], args.split)
            return do_children(i, split[i], kids), True
        if args.split > 0 and i in unk:                  # was too hard before (old run): split instead of 4x budget
            kids = extend_cubes(a, b, k, [cubes[i]], args.split)
            write(i, "SPLIT", unk[i], 0, f"children={len(kids)}")
            return do_children(i, len(kids), kids), True
        budget = args.budget if i not in unk else unk[i] * 4
        if i in unk and unk[i] >= args.max_budget:
            return False, False
        st, model, secs = solve(cubes[i], budget, ('t', i), i, "")
        write(i, st, budget, secs)
        if st == "SAT":
            found(i, cubes[i], model); return True, True
        if st == "UNKNOWN" and args.split > 0:           # too hard for the budget: cut it into smaller cubes
            kids = extend_cubes(a, b, k, [cubes[i]], args.split)
            write(i, "SPLIT", budget, 0, f"children={len(kids)}")
            return do_children(i, len(kids), kids), True
        return False, True

    def steal():
        """own list is finished: take over open cubes and the open CHILDREN of cubes split by other workers"""
        rng = random.Random(w + int(time.time()))
        kidcache = {}
        while True:
            done, unk, split, cdone, cunk = read_state(args.outdir)
            items = []
            for i, nch in split.items():
                if i in done: continue
                items += [("child", i, j) for j in range(nch) if (i, j) not in cdone]
            items += [("cube", i, None) for i in range(len(cubes)) if i not in done and i not in split]
            rng.shuffle(items)
            progressed = False
            for kind, i, j in items:
                if late(): return
                if kind == "child":
                    if (i, j) in cunk and cunk[(i, j)] >= args.max_budget: continue
                    if not claim(f"c{i}_{j}"): continue
                    if i not in kidcache: kidcache[i] = extend_cubes(a, b, k, [cubes[i]], args.split)
                    bud = args.budget if (i, j) not in cunk else cunk[(i, j)] * 4
                    st, model, secs = solve(kidcache[i][j], bud, ('c', i, j), i, f"child:{j}")
                    write(i, st, bud, secs, f"child:{j}")
                    progressed = True
                    if st == "SAT":
                        found(i, kidcache[i][j], model); return
                else:
                    f, pg = handle(i)
                    if f: return
                    progressed = progressed or pg
            if not progressed: return

    mine = [i for i in range(len(cubes)) if i % args.workers == w]
    while True:
        done, unk, split, cdone, cunk = read_state(args.outdir)
        todo = [i for i in mine if i not in done]
        if not todo:
            break
        progressed = False
        for i in todo:
            if late(): return
            f, pg = handle(i)
            if f: return
            progressed = progressed or pg
        if not progressed:
            break
    if args.steal:
        steal()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, default=2); ap.add_argument("--b", type=int, default=3)
    ap.add_argument("--k", type=int, default=4); ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--depth", type=int, default=10)
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--backend", choices=["pysat", "cadical"], default="pysat")
    ap.add_argument("--bin", default="cadical")
    ap.add_argument("--budget", type=int, default=20000, help="conflicts per cube in the first pass")
    ap.add_argument("--split", type=int, default=0, help="cube too hard for the budget -> colour this many more numbers and solve the children (0 = just retry with 4x budget)")
    ap.add_argument("--steal", type=int, default=1, help="1 = a worker that finished its own cubes takes over open cubes / children of other workers (no idle cores at the end)")
    ap.add_argument("--implied", type=int, default=0, help="1 = add implied clauses (2 = also the conditional forced-equality clauses of level 2)  [level 1: (multiples of d use >= j+1 colours when n//d >= R_j); results of a run must then say so")
    ap.add_argument("--max-budget", type=int, default=10**9)
    ap.add_argument("--wall", type=float, default=900, help="seconds per solve call (pysat backend); then interrupt -> UNKNOWN -> split (0 = off)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--worker-id", type=int, default=None, help="internal")
    ap.add_argument("--refine-of", default=None, help="dir of a finished/stopped run: split its still-open cubes further")
    ap.add_argument("--extra", type=int, default=4, help="with --refine-of: how many more numbers to colour")
    ap.add_argument("--deadline-epoch", type=float, default=None, help="internal: stop starting new cubes after this unix time")
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
    if args.implied:   # warm the R_j cache once here, so the workers only read it
        from rado_c1 import rj_value, forced_info
        print(f"[{now()} JST] implied clauses ON (level {args.implied}): R_j table", {j: rj_value(args.a, args.b, j) for j in range(1, args.k)}, flush=True)
        if int(args.implied) >= 2:
            for j in (2, 3):
                if j < args.k: print(f"[{now()} JST] forced_info j={j}:", forced_info(args.a, args.b, j), flush=True)
    shutil.rmtree(os.path.join(args.outdir, "claims"), ignore_errors=True)   # claims are per run
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

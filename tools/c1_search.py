# -*- coding: utf-8 -*-
r"""
C1 search: raise the lower bound of R_4(2(x-y)=3z) (currently "> 225" in arXiv:2210.03262),
or settle it.  Works for any k and any a(x-y)=bz.

Method (adaptive ladder):
  n = (largest n with a recorded SAT) + 1
  run W attempts in parallel (different seeds = different variable orderings), each with a time limit
  * some attempt SAT   -> certificate saved + independently verified, kill the others, go to n+1
  * some attempt UNSAT -> R is settled (recorded as UNSAT; produce a DRAT proof in a separate step!)
  * all attempts time out -> next round for the same n with a longer time limit
The only writer of the results CSV is this program: one row per attempt, append-only,
flush+fsync, JST time.  Resume = just run it again (state is read from the CSV).

Usage (PowerShell, from F:\sat_solver):
  python tools/c1_search.py --a 2 --b 3 --k 4 --base 225 --workers 11 --backend pysat --time-limit 900
Stop with Ctrl+C at any time; nothing already written is lost.
"""
import argparse, csv, json, os, subprocess, sys, time
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
FIELDS = ["jst_time", "a", "b", "k", "n", "seed", "backend", "status", "seconds", "time_limit", "cert", "note"]


def now():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")


def kill_tree(p):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            p.kill()
    except Exception:
        pass


def load_rows(path):
    rows = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    return rows


def append_row(path, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
        f.flush(); os.fsync(f.fileno())


def run_round(args, n, round_idx, tl, here):
    """launch W attempts; return list of result dicts (finished ones) once decided or all done"""
    procs = []
    for w in range(args.workers):
        seed = round_idx * 1000 + w + 1
        cmd = [sys.executable, os.path.join(here, "rado_c1.py"), "solve", "--a", str(args.a), "--b", str(args.b),
               "--k", str(args.k), "--n", str(n), "--seed", str(seed), "--backend", args.backend,
               "--bin", args.bin, "--outdir", args.outdir]
        procs.append((seed, subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)))
    t0 = time.time()
    results, decided = [], None
    pending = dict(procs)
    while pending and decided is None:
        time.sleep(1.0)
        for seed, p in list(pending.items()):
            if p.poll() is not None:
                out, err = p.communicate()
                try:
                    r = json.loads(out.strip().splitlines()[-1])
                except Exception:
                    r = {"jst_time": now(), "a": args.a, "b": args.b, "k": args.k, "n": n, "seed": seed,
                         "backend": args.backend, "status": "ERROR", "seconds": round(time.time() - t0, 2),
                         "cert": "", "note": (err or out)[-200:].replace("\n", " | ")}
                r["time_limit"] = tl
                results.append(r)
                del pending[seed]
                if r["status"] in ("SAT", "UNSAT"):
                    decided = r
        if time.time() - t0 > tl:
            break
    for seed, p in pending.items():
        kill_tree(p)
        try:
            p.communicate(timeout=5)
        except Exception:
            pass
        results.append({"jst_time": now(), "a": args.a, "b": args.b, "k": args.k, "n": n, "seed": seed,
                        "backend": args.backend, "status": "TIMEOUT" if decided is None else "CANCELLED",
                        "seconds": round(time.time() - t0, 2), "time_limit": tl, "cert": "", "note": ""})
    return results, decided


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, default=2)
    ap.add_argument("--b", type=int, default=3)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--base", type=int, default=225, help="published lower bound: R > base. We re-verify SAT at base first.")
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--backend", choices=["pysat", "cadical", "kissat"], default="pysat")
    ap.add_argument("--bin", default="cadical")
    ap.add_argument("--time-limit", type=float, default=900, help="seconds per attempt in round 0")
    ap.add_argument("--time-factor", type=float, default=2.0, help="time limit multiplier per extra round at the same n")
    ap.add_argument("--max-n", type=int, default=1000)
    ap.add_argument("--max-rounds", type=int, default=0, help="give up on an n after this many rounds (0 = never)")
    ap.add_argument("--outdir", default=os.path.join("results", "c1"))
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(args.outdir, exist_ok=True)
    csv_path = os.path.join(args.outdir, f"c1_a{args.a}_b{args.b}_k{args.k}.csv")
    lock = csv_path + ".lock"
    if os.path.exists(lock):
        print(f"[stop] lock exists: {lock}. If no search is running, delete it."); sys.exit(2)
    open(lock, "w").write(str(os.getpid()))
    try:
        while True:
            rows = load_rows(csv_path)
            sat_ns = [int(r["n"]) for r in rows if r["status"] == "SAT"]
            unsat_ns = [int(r["n"]) for r in rows if r["status"] == "UNSAT"]
            best = max(sat_ns) if sat_ns else None
            if unsat_ns:
                print(f"[{now()} JST] UNSAT already recorded at n={min(unsat_ns)}: nothing more to search. (Make a DRAT proof next.)"); break
            n = (best + 1) if best is not None else args.base
            if n > args.max_n:
                print("max-n reached"); break
            tries = sum(1 for r in rows if int(r["n"]) == n and r["status"] in ("TIMEOUT", "ERROR"))   # ERROR counts too (no endless loop)
            round_idx = tries // args.workers
            if args.max_rounds and round_idx >= args.max_rounds:
                print(f"[{now()} JST] n={n}: {args.max_rounds} rounds timed out -> give up (no colouring found yet)"); break
            tl = args.time_limit * (args.time_factor ** round_idx)
            print(f"[{now()} JST] best SAT n={best}; trying n={n}, round {round_idx}, {args.workers} workers, limit {tl:.0f}s", flush=True)
            results, decided = run_round(args, n, round_idx, tl, here)
            for r in results:
                append_row(csv_path, r)
            if decided is not None:
                print(f"[{now()} JST] n={n}: {decided['status']} (seed {decided['seed']}, {decided['seconds']}s) {decided.get('cert','')}", flush=True)
                if decided["status"] == "UNSAT":
                    print(f"=> R_{args.k}({args.a}(x-y)={args.b}z) = {n}  (needs a DRAT proof before it counts)"); break
            else:
                print(f"[{now()} JST] n={n}: all {args.workers} attempts timed out", flush=True)
    except KeyboardInterrupt:
        print("\n[interrupted] rows already written are kept; run again to resume")
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


if __name__ == "__main__":
    main()

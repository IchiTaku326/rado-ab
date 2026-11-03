# -*- coding: utf-8 -*-
r"""Structured colourings (lower bounds) for k colours (2026-11-01).  The colour of x may depend only on
(min(v_a(x), VMAX), x // L)  (v_a = how many times a divides x).  This cuts the variables ~L times and was what made
[1,460] (3,4), [1,940] (4,5), [1,925] (2,5) colourable with 4 colours in minutes (unstructured SAT stopped at 449/699/685).
Conjecture K4/recurrence: R_k = b*(R_{k-1} + 2a) + 1  -> try n = predicted - 1.
Each job runs in its own process with a hard time limit (killed, no hang).  A SAT answer is turned into a colouring of
[1,n] and CHECKED DIRECTLY (every solution of a(x-y)=bz in [1,n]); only then it is saved:
results\c1_k4ab\cert_a{a}_b{b}_k{k}_n{n}_structured.json and a SAT row in results\c1_k4ab\c1_a{a}_b{b}_k{k}.csv
(so 86 / k4_scan know [1,n] is colourable).  Results also in results\struct_color.csv.  Resumable (done jobs skipped).
Jobs: a,b,k,n,L   Run: python tools\struct_color.py --workers 2 --wall 14400 3,5,4,960,2 3,4,5,1868,2"""
import csv, json, os, sys, time, subprocess, tempfile
import multiprocessing as mp
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "..", "results"); D = os.path.join(RES, "c1_k4ab")
OUT = os.path.join(RES, "struct_color.csv"); VMAX = 3


def vala(x, a):
    v = 0
    while x % a == 0: x //= a; v += 1
    return v


def build(a, b, k, n, L):
    key = lambda x: (min(vala(x, a), VMAX), x // L)
    keys = sorted({key(x) for x in range(1, n + 1)}); kid = {kk: i for i, kk in enumerate(keys)}
    cl = [[k * i + c + 1 for c in range(k)] for i in range(len(keys))]
    seen = set()
    for s in range(1, n // a + 1):
        z = a * s; d = b * s
        if d >= n: break
        kz = kid[key(z)]
        for y in range(1, n - d + 1):
            T = tuple(sorted({kid[key(y)], kid[key(y + d)], kz}))
            if T in seen: continue
            seen.add(T)
            for c in range(k): cl.append([-(k * t + c + 1) for t in T])
    cl.append([k * kid[key(1)] + 1])                                # colour symmetry
    return keys, kid, key, cl


def child(a, b, k, n, L, path):
    keys, kid, key, cl = build(a, b, k, n, L)
    binp = os.environ.get("CADICAL_BIN")
    if binp:                                                         # Linux test path: external cadical
        f = path + ".cnf"; open(f, "w").write(f"p cnf {k*len(keys)} {len(cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in cl))
        out = subprocess.run([binp, "-q", f], capture_output=True, text=True).stdout
        model = [int(t) for l in out.splitlines() if l.startswith("v") for t in l.split()[1:]] if "s SATISFIABLE" in out else None
        res = "SAT" if model else ("UNSAT" if "UNSATISFIABLE" in out else "ERROR")
    else:
        from pysat.solvers import Solver
        with Solver(name="cadical153", bootstrap_with=cl) as s:
            ok = s.solve(); model = s.get_model() if ok else None; res = "SAT" if ok else "UNSAT"
    col = None
    if model:
        pos = set(l for l in model if l > 0)
        col = [None] + [next(c for c in range(k) if k * kid[key(x)] + c + 1 in pos) for x in range(1, n + 1)]
    json.dump({"res": res, "col": col, "classes": len(keys)}, open(path, "w"))


def check(a, b, n, C):
    bad = 0
    for s in range(1, n // a + 1):
        z = a * s; d = b * s
        if d >= n: break
        cz = C[z]
        for y in range(1, n - d + 1):
            if C[y] == cz and C[y + d] == cz: bad += 1
    return bad


def job(arg):
    j, wall = arg; a, b, k, n, L = map(int, j.split(","))
    t0 = time.time(); fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    p = mp.Process(target=child, args=(a, b, k, n, L, path)); p.start(); p.join(wall)
    if p.is_alive():
        p.terminate(); p.join(10)
        try: os.remove(path)
        except OSError: pass
        return j, "TIMEOUT", "", round(time.time() - t0, 1)
    try: r = json.load(open(path))
    except Exception: return j, "ERROR", "", round(time.time() - t0, 1)
    finally:
        for f in (path, path + ".cnf"):
            try: os.remove(f)
            except OSError: pass
    if r["res"] != "SAT": return j, r["res"], "", round(time.time() - t0, 1)
    C = r["col"]; bad = check(a, b, n, C)
    if bad: return j, f"CHECK_FAILED_{bad}", "", round(time.time() - t0, 1)
    os.makedirs(D, exist_ok=True)
    cert = os.path.join(D, f"cert_a{a}_b{b}_k{k}_n{n}_structured.json")
    json.dump({"a": a, "b": b, "k": k, "n": n, "seed": f"structured_L{L}", "backend": "cadical", "coloring": C[1:]}, open(cert, "w"))
    f = os.path.join(D, f"c1_a{a}_b{b}_k{k}.csv")
    hdr = ["jst_time", "a", "b", "k", "n", "seed", "backend", "status", "seconds", "time_limit", "cert", "note"]
    new = not os.path.exists(f)
    if not new: hdr = open(f, encoding="utf-8").readline().strip().split(",")
    with open(f, "a", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=hdr)
        if new: w.writeheader()
        row = {x: "" for x in hdr}
        row.update(jst_time=datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), a=a, b=b, k=k, n=n, seed="structured", backend="cadical",
                   status="SAT", seconds=round(time.time() - t0, 1), time_limit=wall, cert=os.path.relpath(cert, os.path.join(HERE, "..")),
                   note=f"structured L={L}, checked: 0 monochromatic solutions")
        w.writerow(row)
    return j, "SAT", cert, round(time.time() - t0, 1)


def main():
    args = sys.argv[1:]; W, wall = 2, 14400.0
    while args and args[0].startswith("--"):
        k_, v_ = args[0], args[1]; args = args[2:]
        if k_ == "--workers": W = int(v_)
        elif k_ == "--wall": wall = float(v_)
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            if r["result"] in ("SAT", "UNSAT"): done.add(r["job"])
    jobs = [j for j in args if j not in done]
    print(f"{len(jobs)} jobs ({len(args) - len(jobs)} done), {W} at a time, at most {wall/3600:.1f} h each", flush=True)
    new = not os.path.exists(OUT); fh = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["jst_time", "job", "result", "cert", "seconds"]); fh.flush()
    t0 = time.time()
    from concurrent.futures import ThreadPoolExecutor, as_completed      # threads: each job starts its own killable process
    with ThreadPoolExecutor(max_workers=W) as ex:
        futs = [ex.submit(job, (j, wall)) for j in jobs]
        for i, fu in enumerate(as_completed(futs), 1):
            j, res, cert, sec = fu.result()
            w.writerow([datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), j, res, cert, sec]); fh.flush(); os.fsync(fh.fileno())
            left = len(jobs) - i
            print(f"[{datetime.now(JST):%H:%M:%S}] {j}: {res} ({sec}s) {cert} | {i}/{len(jobs)}, at most about {(-(-left // W)) * wall / 3600:.1f} h more", flush=True)
    print("done (results\\struct_color.csv)")


if __name__ == "__main__":
    mp.freeze_support(); main()

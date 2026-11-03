# -*- coding: utf-8 -*-
r"""
Generic resumable job runner for long computations (SAT / cube-and-conquer / scans).

Design goals (SPEC section 6):
  * Append-only results: a finished job's row is written once and NEVER rewritten.
  * Every row has JST start/end time. Every job keeps its own full log file.
  * Flush + fsync after every row. Killing the program (Ctrl+C, power off) loses
    at most the jobs that were running at that moment; they are simply re-run.
  * Resume: jobs whose job_id is already in the results CSV are skipped.
  * Snapshots: the results CSV is copied to results\snapshots\ with a timestamp
    every --snapshot-minutes (default 30). Old snapshots are never deleted.
  * One runner per results file (lock file) so two runs cannot corrupt it.

Jobs file (CSV with header):  job_id,cmd
  job_id : unique text (used as the log file name; keep it simple: a-z 0-9 _ - .)
  cmd    : shell command line to run for this job (one job = one short-ish piece
           of work; split big problems into many jobs, e.g. cubes).

Usage (PowerShell, from F:\sat_solver):
  python tools/jobrunner.py --jobs jobs/example_jobs.csv --out results/example_results.csv --workers 11 --timeout 3600
"""
import argparse, csv, hashlib, os, re, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
FIELDS = ["job_id", "jst_start", "jst_end", "seconds", "returncode", "status", "log_tail"]


ACTIVE = set()
ACTIVE_LOCK = threading.Lock()


def kill_tree(proc):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc.kill()
    except Exception:
        pass


def now():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")


def safe(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:120]


def load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                done.add(r["job_id"])
    return done


def acquire_lock(path):
    lock = path + ".lock"
    if os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip())
        except Exception:
            pid = None
        print(f"[stop] lock file exists: {lock} (pid {pid}). If no runner is active, delete that file.")
        sys.exit(2)
    with open(lock, "w") as f:
        f.write(str(os.getpid()))
    return lock


def run_job(job_id, cmd, timeout, logdir):
    start = now()
    t0 = time.time()
    log_path = os.path.join(logdir, safe(job_id) + ".log")
    status, rc = "ok", 0
    try:
        with open(log_path, "a", encoding="utf-8", errors="replace") as lf:
            lf.write(f"# {start} JST  cmd: {cmd}\n")
            lf.flush()
            p = subprocess.Popen(cmd, shell=True, stdout=lf, stderr=subprocess.STDOUT)
            with ACTIVE_LOCK:
                ACTIVE.add(p)
            try:
                rc = p.wait(timeout=timeout)
            finally:
                with ACTIVE_LOCK:
                    ACTIVE.discard(p)
            if rc != 0:
                status = "error"
    except subprocess.TimeoutExpired:
        kill_tree(p)
        status, rc = "timeout", -1
    except Exception as e:  # noqa
        status, rc = "error", -2
        with open(log_path, "a", encoding="utf-8", errors="replace") as lf:
            lf.write(f"# runner exception: {e}\n")
    tail = ""
    try:
        with open(log_path, "rb") as lf:
            lf.seek(0, os.SEEK_END)
            lf.seek(max(0, lf.tell() - 300))
            tail = lf.read().decode("utf-8", "replace").replace("\r", " ").replace("\n", " | ")
    except Exception:
        pass
    return [job_id, start, now(), round(time.time() - t0, 2), rc, status, tail]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--timeout", type=float, default=None, help="seconds per job (default: none)")
    ap.add_argument("--snapshot-minutes", type=float, default=30)
    ap.add_argument("--retry-failed", action="store_true",
                    help="also re-run jobs recorded as error/timeout (their old rows stay; a new row is appended)")
    a = ap.parse_args()

    out_dir = os.path.dirname(a.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    snapdir = os.path.join(out_dir, "snapshots")
    logdir = os.path.join(out_dir, "logs")
    os.makedirs(snapdir, exist_ok=True)
    os.makedirs(logdir, exist_ok=True)

    with open(a.jobs, newline="", encoding="utf-8") as f:
        jobs = [(r["job_id"], r["cmd"]) for r in csv.DictReader(f)]
    ids = [j[0] for j in jobs]
    if len(ids) != len(set(ids)):
        print("[stop] duplicate job_id in jobs file"); sys.exit(2)

    ok_ids, all_ids = set(), set()
    if os.path.exists(a.out):
        with open(a.out, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                all_ids.add(r["job_id"])
                if r["status"] == "ok":
                    ok_ids.add(r["job_id"])
    skip = all_ids if not a.retry_failed else ok_ids
    todo = [j for j in jobs if j[0] not in skip]

    lock = acquire_lock(a.out)
    print(f"[{now()} JST] jobs={len(jobs)} done={len(skip)} todo={len(todo)} workers={a.workers} -> {a.out}")
    new_file = not os.path.exists(a.out)
    last_snap = time.time()
    written = 0
    stop = False
    try:
        with open(a.out, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(FIELDS); f.flush(); os.fsync(f.fileno())
            ex = ThreadPoolExecutor(max_workers=a.workers)
            futs = [ex.submit(run_job, jid, cmd, a.timeout, logdir) for jid, cmd in todo]
            try:
                for fu in as_completed(futs):
                    w.writerow(fu.result()); f.flush(); os.fsync(f.fileno())
                    written += 1
                    if written % 10 == 0:
                        print(f"  [{now()} JST] {written}/{len(todo)}")
                    if time.time() - last_snap > a.snapshot_minutes * 60:
                        snap = os.path.join(snapdir, os.path.basename(a.out).rsplit(".", 1)[0] +
                                            datetime.now(JST).strftime("_%Y%m%d_%H%M%S.csv"))
                        shutil.copyfile(a.out, snap)
                        last_snap = time.time()
            except KeyboardInterrupt:
                print("\n[interrupted] cancelling queued jobs; running jobs are not recorded and will re-run on resume")
                stop = True
                for fu in futs:
                    fu.cancel()
                with ACTIVE_LOCK:
                    for pr in list(ACTIVE):
                        kill_tree(pr)
                ex.shutdown(wait=True, cancel_futures=True)
            else:
                ex.shutdown(wait=True)
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass
    snap = os.path.join(snapdir, os.path.basename(a.out).rsplit(".", 1)[0] + datetime.now(JST).strftime("_%Y%m%d_%H%M%S_final.csv"))
    if os.path.exists(a.out):
        shutil.copyfile(a.out, snap)
    print(f"[{now()} JST] finished this run: wrote {written} rows{' (interrupted)' if stop else ''}")


if __name__ == "__main__":
    main()

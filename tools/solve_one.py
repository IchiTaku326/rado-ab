# -*- coding: utf-8 -*-
"""Solve one DIMACS file with a pysat solver and print SAT / UNSAT (used as a killable subprocess).
Run: python tools\\solve_one.py file.cnf cadical153"""
import sys
from pysat.formula import CNF
from pysat.solvers import Solver
f = CNF(from_file=sys.argv[1])
with Solver(name=sys.argv[2] if len(sys.argv) > 2 else "cadical153", bootstrap_with=f.clauses) as s:
    print("SAT" if s.solve() else "UNSAT", flush=True)

#!/usr/bin/env bash
# Step 1: the LRAT proof of the symbolic family formula for R_3(a(x-y)=(a+1)z) <= a^3+5a^2+8a, a >= 28 (paper 1, Section 6).
# Needs bin_linux/lrat-check and bin_linux/cake_lpr (see bin_linux/README.md). About a minute.
# Expected: "c VERIFIED" (lrat-check) and "s VERIFIED UNSAT" (cake_lpr).
cd "$(dirname "$0")"
cat results/sym_j1/summary.txt
echo "--- lrat-check:"
bin_linux/lrat-check results/sym_j1/family.cnf results/sym_j1/family.lrat
echo "--- cake_lpr (formally verified):"
bin_linux/cake_lpr results/sym_j1/family.cnf results/sym_j1/family.lrat

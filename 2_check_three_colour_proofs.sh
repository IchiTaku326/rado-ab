#!/usr/bin/env bash
# Step 2: for every pair 2 <= a < b <= 60 (gcd 1, except (2,3)) regenerate the small-set CNF at n = N(a,b) (n = 181 for (2,5)),
# let CaDiCaL write an LRAT proof, and check it with lrat-check and cake_lpr. Resumable (run again to continue).
# About a day on 11 cores and 32 GB; the proofs for b = 57..60 need cake_lpr with a 14 GB heap (one at a time).
# Results: results/proofcheck_subset.csv (one row per cell), last line of results/proofcheck_subset_FINAL.txt.
# Expected: "(B) 3 colours b <= 60: 1041/1041 cells VERIFIED", with result VERIFIED_CAKE in every row.
# Our own run: results/recorded/.
cd "$(dirname "$0")"
WORKERS="${WORKERS:-11}"
CAKE_BIG=cake_lpr_14g python3 tools/verify_subset.py --workers "$WORKERS" --bmax 60 --formula 1 --only-b 1 --wall 14400
tail -1 results/proofcheck_subset_FINAL.txt

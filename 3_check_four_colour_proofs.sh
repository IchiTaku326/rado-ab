#!/usr/bin/env bash
# Step 3: R_4(3(x-y)=4z) <= 461, R_4(5(x-y)=4z) <= 741, R_4(6(x-y)=5z) <= 1501 (paper 2).
# Checks that the cube trees in results/subset_cubes.csv are complete, and gives every leaf cube a CaDiCaL LRAT proof
# checked by lrat-check and cake_lpr. Resumable. Many hours on 11 cores.
# Expected: tree complete YES; 22863, 813 and 6833 leaf cubes VERIFIED_CAKE (see results/proofcheck_subset.csv).
cd "$(dirname "$0")"
WORKERS="${WORKERS:-11}"
python3 tools/verify_subset.py --workers "$WORKERS" --cube-jobs "4,3,4,461,109 4,5,4,741,141 4,6,5,1501,241" --wall 3600
tail -1 results/proofcheck_subset_FINAL.txt

#!/usr/bin/env bash
# Step 3: R_4(3(x-y)=4z) <= 461, R_4(5(x-y)=4z) <= 741, R_4(6(x-y)=5z) <= 1501, and (version 2)
# R_4(4(x-y)=3z) <= 313, R_4(5(x-y)=2z) <= 625, R_4(5(x-y)=3z) <= 625, R_4(x-y=5z) <= 2001 (paper 2).
# Checks that the cube trees in results/subset_cubes.csv are complete, and gives every leaf cube a CaDiCaL LRAT proof
# checked by lrat-check and cake_lpr. Resumable. About two days on 11 cores.
# Expected (last line of results/proofcheck_subset_FINAL.txt): tree complete YES; per job k4_3_4_461 22863/22863,
# k4_5_4_741 813/813, k4_6_5_1501 6833/6833, k4_4_3_313 715/715, k4_5_2_625 715/715, k4_5_3_625 715/715, k4_1_5_2001 3438/3438.
cd "$(dirname "$0")"
WORKERS="${WORKERS:-11}"
python3 tools/verify_subset.py --workers "$WORKERS" --cube-jobs "4,3,4,461,109 4,5,4,741,141 4,6,5,1501,241 4,4,3,313,73 4,5,2,625,125 4,5,3,625,125 4,1,5,2001,286" --wall 3600
tail -1 results/proofcheck_subset_FINAL.txt

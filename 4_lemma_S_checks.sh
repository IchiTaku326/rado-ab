#!/usr/bin/env bash
# Step 4: the lower part of Conjecture S (paper 1, Section 7.3) for all main-region pairs with b <= 30, with CaDiCaL
# (no proof files). (i) the base case: results/lemmaS/BASE_CHECK.txt, expected SAT only for (2,3) and (2,5);
# (ii) the steps m = a+1..max(ab+4a,4b): results/lemmaS/LOWER_SUMMARY.txt, expected NOT_FORCED only for (2,3).
# About 2 hours on 11 cores. Resumable (step (ii)). Our own run: results/recorded/lemmaS/.
cd "$(dirname "$0")"
WORKERS="${WORKERS:-11}"
mkdir -p results/lemmaS
python3 tools/research/lemma_S_induction/base_check.py 3 30 bin_linux/cadical | tee results/lemmaS/BASE_CHECK.txt
python3 tools/research/lemma_S_induction/lower_table2.py --bmax 30 --workers "$WORKERS" --cadical bin_linux/cadical

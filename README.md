# Rado numbers of a(x − y) = bz — papers, programs and results

Two preprints (not peer reviewed) by Takumi Ichikawa, with all programs and the recorded results.

For coprime positive integers a, b, the Rado number **R_k(a,b)** is the least n such that every colouring of {1,…,n}
with k colours contains a monochromatic solution of `a(x − y) = bz` (x, y, z need not be distinct).

| Paper | File |
|---|---|
| 1. *Rado numbers of a(x−y)=bz with a<b: two colours, lower bounds for every number of colours, and the three-colour upper bound up to one statement* (version 2, 21 pages) | `paper1/Ichikawa_Rado_numbers_with_a_less_than_b.pdf` |
| 2. *Four-colour Rado numbers of a(x−y)=bz: seven values with checked proofs* (version 2, 7 pages) | `paper2/Ichikawa_four-colour_Rado_numbers.pdf` |

**DOIs (Zenodo):**
paper 1: version 1 https://doi.org/10.5281/zenodo.23902080, all versions https://doi.org/10.5281/zenodo.23902079 ·
paper 2: version 2 https://doi.org/10.5281/zenodo.23933854, all versions https://doi.org/10.5281/zenodo.23902620 ·
this repository, release v1: https://doi.org/10.5281/zenodo.23902480
(later releases get their own DOIs; all versions are listed on the Zenodo record page).

Earlier note (separate record): R₄(2(x−y)=3z) = 226, https://doi.org/10.5281/zenodo.23582301 (code: https://github.com/IchiTaku326/rado-226).

## Results and their status

Notation (paper 1): R2 = b²+b+1, M = b(R2+a), A = {au′+bu : 1 ≤ u,u′ ≤ b}, m′ = min{m ∈ A : am > M},
N(a,b) = min(am′, M+ab+1). Main region: a²+(b−1)a ≤ b²+b+1 (there N = b(b²+b+2a+1)+1). D = a²+ab−b².

| Statement | Status |
|---|---|
| R₂(a,b) = b²+b+1 (1 < a < b) | known (Yao 2014); new proof via uniqueness |
| the extremal 2-colouring is unique ((a,b) ≠ (2,3)) | **proved** (paper 1, Thm 1.1) |
| R₃(a,b) ≥ N(a,b) for all a < b | **proved** (paper 1, Thm 1.2) |
| R₃(a,a+1) = a³+5a²+8a for all a ≥ 7 | **proved**, computer-assisted (symbolic SAT certificate checked by `cake_lpr`) |
| R_k(a,b) > b^k for all k, a < b; R_k ≥ L_k when D ≤ 1 or a+1 ≤ D ≤ 2a | **proved** (paper 1, Thms 1.4, 4.5) |
| R₃ ≤ N(a,b) follows from Conjecture S | **proved** (paper 1, Thm 1.6) |
| Conjecture S follows from its "lower part" (the first max(ab+4a,4b) multiples of a) | **proved** (paper 1, Thm 7.6) |
| lower part of Conjecture S, main region, b ≤ 30 (except (2,3), (2,5), where it is false) | SAT solver only (no proof files) |
| **Conjecture S in general** | **open** |
| R₃(a,b) = N(a,b) for all pairs with b ≤ 60, except R₃(2,3) = 61 and R₃(2,5) = 181 | upper bounds: LRAT proofs for all 1041 pairs except (2,3), checked by `lrat-check` and `cake_lpr`; (2,3) is a small computation |
| the same for all 1939 pairs with b ≤ 81 | SAT solver only (MiniSat, no proof files) |
| R₄(3,4) = 461, R₄(5,4) = 741, R₄(6,5) = 1501 | colouring + cube-and-conquer, every leaf proof checked by `cake_lpr` (paper 2) |
| R₄(4(x−y)=3z) = 313, R₄(5(x−y)=2z) = R₄(5(x−y)=3z) = 625, R₄(x−y=5z) = 2001 | the same (paper 2, version 2) |
| R₅(4(x−y)=3z) ≥ 1401: the formula of Conjecture H3 (1273) fails for five colours | explicit colouring, checked |
| R₄(3,5) ≥ 961, R₄(2,5) ≥ 951, R₄(4,5) ≥ 961, R₅(3,4) ≥ 1869, R₅(3(x−y)=2z) ≥ 399 | explicit colourings, checked |
| R₄(3,5) = 961? | **open** (our searches did not finish) |
| growth of R_k in k (exponential?) | **open**; best upper bound known to us: Sanders 2026, exp(k^{2+o(1)}) |

"a < b" means the coefficient of x − y is the smaller one. Values where a > b (for example R₄(5,4)) are written
R₄(5(x−y)=4z) in the papers to avoid confusion.

## Reproduce

Requirements:

- steps 0 and 5: any system with Python 3 + numpy (step 0) or LaTeX with latexmk (step 5);
- steps 1–4: **Linux** (on Windows: WSL; on macOS: a Linux virtual machine or container), Python 3 + numpy, and the
  binaries in `bin_linux/`, built from source as described in `bin_linux/README.md` (CaDiCaL, drat-trim, lrat-check,
  cake_lpr).

On Linux, macOS or WSL run the `.sh` files, for example `bash 0_check_lower_bounds.sh`; set the number of cores with
`WORKERS=8 bash 2_check_three_colour_proofs.sh` (default 11). On Windows the `.bat` files of the same names call WSL.
Every step is resumable: run it again to continue. All six steps were tested on a fresh copy of this repository on
Ubuntu 24.04 (Python 3.13, numpy 2.5), with the binaries built from source as in `bin_linux/README.md`
(steps 2–4 on small ranges only).

| Step | What it checks | Time (11 cores) | Expected |
|---|---|---|---|
| `0_check_lower_bounds` | all lower-bound colourings of both papers, by an independent checker (`tools/check_lower_bounds.py`) | seconds | `ALL GOOD` |
| `1_check_family_proof` | the LRAT proof for R₃(a,a+1) ≤ N, a ≥ 28 (`results/sym_j1/`), with `lrat-check` and `cake_lpr` | about a minute | `c VERIFIED`, `s VERIFIED UNSAT` |
| `2_check_three_colour_proofs` | regenerates and checks the 1041 three-colour proofs (b ≤ 60) | about a day; b = 57…60 need `cake_lpr` with a 14 GB heap | `results/proofcheck_subset_FINAL.txt`: 1041/1041 cells VERIFIED, rows `VERIFIED_CAKE` |
| `3_check_four_colour_proofs` | completeness of the cube trees and a checked proof for every leaf (461, 741, 1501, 313, 625, 625, 2001) | about two days | last line of `results/proofcheck_subset_FINAL.txt`: tree complete YES; per job k4_3_4_461 22863/22863, k4_5_4_741 813/813, k4_6_5_1501 6833/6833, k4_4_3_313 715/715, k4_5_2_625 715/715, k4_5_3_625 715/715, k4_1_5_2001 3438/3438 VERIFIED |
| `4_lemma_S_checks` | the base case and the steps of the lower part of Conjecture S, b ≤ 30 | about 2 hours | base case: SAT only for (2,3) and (2,5); steps: NOT_FORCED only for (2,3) |
| `5_build_papers` | builds both PDFs (LaTeX with latexmk; or upload `main.tex` to Overleaf) | seconds | |

Steps 2 and 3 write `results/proofcheck_subset.csv`; the rows of our own run are in `results/recorded/` for comparison.
The LRAT proofs themselves are not stored (too large), except the one of step 1.

Optional: `python3 tools/sym_family.py 1 10 10 12 60` regenerates the family formula of step 1 (it overwrites
`results/sym_j1/`; `git diff --stat` should then show no change of `family.cnf`).

## What the results depend on (possible weak points)

1. **Encodings.** The CNF of the small set S (paper 1, Lemma 5.1) contains only clauses of the full problem, plus colour
   symmetry breaking. Every clause is re-checked against the equation by an independent routine before it is written.
2. **Symmetry breaking** (first fit / smallest element colour 0) is argued in the papers, not machine-checked.
3. **Completeness of the cube trees** (paper 2) is checked by a separate routine in `tools/verify_subset.py`, not formally.
4. **Checkers.** `lrat-check` and the formally verified `cake_lpr` (CakeML) both accepted every proof.
5. **Lower part of Conjecture S** (paper 1, Section 7.3) is a SAT-solver result without proof files. It is not used for
   any value: all values for b ≤ 60 rest on the checked proofs of step 2.
6. **Literature.** The literature check is not exhaustive. Yao's paper (Ars Combin. 113, 2014) was read only as an abstract.
   If a value here is already published, please open an issue.

## Layout

```
paper1/, paper2/    LaTeX source, figure, PDF
tools/              all programs of the project (research/ = exploratory scripts; some contain paths of the machine they ran on)
                    check_lower_bounds.py   independent checker of all lower bounds (written for this release)
                    research/lower_search2.py  search for good colourings above a formula (five colours, paper 2)
                    verify_subset.py        regenerates the small-set CNFs, runs CaDiCaL --lrat, lrat-check and cake_lpr
                    subset_cubes.py         cube-and-conquer search on the small set (produced results/subset_cubes.csv)
                    sym_family.py           symbolic family proof for b = a+1 (produced results/sym_j1/)
                    research/lemma_S_induction/  lower_table2.py, base_check.py (Conjecture S, Section 7.3)
results/            lower_bounds/ (colourings), sym_j1/ (formula + LRAT proof), subset_cubes.csv (cube trees),
                    subset_K_bb1.csv, s_min3.csv, subset_check.csv (three-colour SAT results), cegar/ (searches for (3,5), (2,5)),
                    recorded/ (our proof-check rows and FINAL lines, Lemma S tables)
bin_linux/          where the solver and checker binaries go (not included)
```

## Licence

Code: MIT (`LICENSE`). Papers (`paper1/`, `paper2/`): Creative Commons Attribution 4.0 (CC BY 4.0).
Japanese version of this file: `README.ja.md`.

## Disclosure

Programs, computation plans, parts of the proofs and parts of the text were developed with the help of an AI assistant
(Claude, Anthropic). The author checked the proofs and is responsible for the content.

## Computing environment

Intel Core i5-11400F (6 cores, 12 threads), 32 GB DDR4, NVIDIA GeForce RTX 3060 (not used), Windows 11 Home 64-bit (solvers run in WSL / Linux), some runs in a Linux cloud sandbox.
CaDiCaL 3.0.1 (commit c607304), drat-trim / lrat-check (commit 2e3b2dc), cake_lpr (commit a36874a), MiniSat 2.2 and CaDiCaL 1.5.3 through PySAT for the searches. Details: Section 8 of paper 1 and Section 5 of paper 2.

# bin_linux

The proof-check steps 1–4 (run inside Linux; on Windows in WSL) look for these executables here. They are **not**
stored in this repository. Build them from source in a folder **outside** the repository, for example `~/src`, and copy
them here. Run these lines from the repository root (tested on Ubuntu 24.04 with gcc, make and git installed):

```
mkdir -p ~/src
# CaDiCaL (SAT solver that writes LRAT proofs), MIT licence. We used version 3.0.1 (commit c607304).
git clone https://github.com/arminbiere/cadical ~/src/cadical
(cd ~/src/cadical && ./configure && make -j4)
cp ~/src/cadical/build/cadical bin_linux/

# drat-trim and lrat-check (proof checkers), MIT licence. We used commit 2e3b2dc.
git clone https://github.com/marijnheule/drat-trim ~/src/drat-trim
(cd ~/src/drat-trim && make)
cp ~/src/drat-trim/drat-trim bin_linux/
gcc -O2 -o bin_linux/lrat-check ~/src/drat-trim/lrat-check.c

# cake_lpr (formally verified LRAT/LPR checker, CakeML). We used commit a36874a.
# Three builds with different heap and stack sizes (MB). Do NOT add -std=c99: then aligned_alloc is not declared
# and the checker crashes (segmentation fault).
git clone https://github.com/tanyongkiam/cake_lpr ~/src/cake_lpr
gcc -O2 -static ~/src/cake_lpr/basis_ffi.c ~/src/cake_lpr/cake_lpr.S -o bin_linux/cake_lpr     -DCML_HEAP_SIZE=700   -DCML_STACK_SIZE=100
gcc -O2 -static ~/src/cake_lpr/basis_ffi.c ~/src/cake_lpr/cake_lpr.S -o bin_linux/cake_lpr_big -DCML_HEAP_SIZE=4000  -DCML_STACK_SIZE=1000
gcc -O2 -static ~/src/cake_lpr/basis_ffi.c ~/src/cake_lpr/cake_lpr.S -o bin_linux/cake_lpr_14g -DCML_HEAP_SIZE=14000 -DCML_STACK_SIZE=1000
```

Quick test: `bash 1_check_family_proof.sh` must print `c VERIFIED` and `s VERIFIED UNSAT`.

`tools/verify_subset.py` uses `cake_lpr` for small proofs and the file named by the environment variable `CAKE_BIG`
(default `cake_lpr_big`) for the large three-colour proofs. The step `2_check_three_colour_proofs` sets
`CAKE_BIG=cake_lpr_14g`, because the proofs for 57 <= b <= 60 need a heap of up to 14 GB (one such check at a time
needs about 17 GB of memory). Newer cake_lpr versions also accept `--CML_HEAP_SIZE=<MB>` on the command line.

If `cake_lpr` cannot be started, `verify_subset.py` still checks every proof with `lrat-check`; the result is then
`VERIFIED` instead of `VERIFIED_CAKE`.

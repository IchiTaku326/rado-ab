#!/usr/bin/env bash
# Step 0: checks every lower-bound colouring of both papers with an independent program (seconds). Expected: ALL GOOD
cd "$(dirname "$0")"
python3 tools/check_lower_bounds.py 34

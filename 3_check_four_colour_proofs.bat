@echo off
rem Step 3: cube trees and leaf proofs for 461, 741, 1501, 313, 625, 625, 2001 (paper 2). About two days. Resumable.
cd /d %~dp0
wsl -e bash -c "cd \"$(wslpath '%~dp0')\" && WORKERS=11 bash 3_check_four_colour_proofs.sh"
pause

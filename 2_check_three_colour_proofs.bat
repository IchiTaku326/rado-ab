@echo off
rem Step 2: regenerate and check the 1041 three-colour proofs (b <= 60) with lrat-check and cake_lpr. About a day. Resumable.
rem Needs WSL and bin_linux (see bin_linux\README.md). Set the number of cores below.
cd /d %~dp0
wsl -e bash -c "cd \"$(wslpath '%~dp0')\" && WORKERS=11 bash 2_check_three_colour_proofs.sh"
pause

@echo off
rem Step 1: LRAT proof of the family formula for R_3(a(x-y)=(a+1)z) <= a^3+5a^2+8a, a >= 28. Needs WSL and bin_linux (see bin_linux\README.md).
cd /d %~dp0
wsl -e bash -c "cd \"$(wslpath '%~dp0')\" && bash 1_check_family_proof.sh"
pause

@echo off
rem Step 4: lower part of Conjecture S, main region, b <= 30 (CaDiCaL, no proof files). About 2 hours.
cd /d %~dp0
wsl -e bash -c "cd \"$(wslpath '%~dp0')\" && WORKERS=11 bash 4_lemma_S_checks.sh"
pause

@echo off
rem Step 0: checks every lower-bound colouring of both papers with an independent program (seconds). Expected: ALL GOOD
rem Needs Python 3 with numpy (Windows or WSL).
cd /d %~dp0
python tools\check_lower_bounds.py 34
pause

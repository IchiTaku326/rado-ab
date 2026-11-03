@echo off
rem Builds both papers: needs a LaTeX installation (MiKTeX or TeX Live) with latexmk.
rem No LaTeX? Upload paper1\main.tex (with fig_golden.pdf) or paper2\main.tex to https://www.overleaf.com
cd /d %~dp0paper1
latexmk -pdf -interaction=nonstopmode main.tex
cd /d %~dp0paper2
latexmk -pdf -interaction=nonstopmode main.tex
pause

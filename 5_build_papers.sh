#!/usr/bin/env bash
# Builds both papers (needs LaTeX with latexmk). Without LaTeX: upload paper1/main.tex (+ fig_golden.pdf) or paper2/main.tex to Overleaf.
cd "$(dirname "$0")"
(cd paper1 && latexmk -pdf -interaction=nonstopmode main.tex)
(cd paper2 && latexmk -pdf -interaction=nonstopmode main.tex)

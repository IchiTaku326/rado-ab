# -*- coding: utf-8 -*-
r"""Build chat_results_INDEX.md (run by the human, NOT by agents).
Lists every .md in chat_results\ with its first heading and modified time (JST).
Usage (PowerShell, from F:\sat_solver):  python tools/make_chat_index.py
"""
import os
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
d = "chat_results"
rows = []
for name in sorted(os.listdir(d)):
    if not name.endswith(".md") or name == "README.md":
        continue
    p = os.path.join(d, name)
    title = ""
    with open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#"):
                title = line.lstrip("# ").strip(); break
    t = datetime.fromtimestamp(os.path.getmtime(p), JST).strftime("%Y-%m-%d %H:%M")
    rows.append(f"| {t} | [{name}](chat_results/{name}) | {title} |")
now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
with open("chat_results_INDEX.md", "w", encoding="utf-8") as f:
    f.write(f"# chat_results 一覧(生成: {now} JST)\n\n| 更新(JST) | ファイル | 題名 |\n|---|---|---|\n")
    f.write("\n".join(rows) + "\n")
print(f"{len(rows)} files -> chat_results_INDEX.md")

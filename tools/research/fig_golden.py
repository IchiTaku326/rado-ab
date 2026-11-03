"""Figure for paper 1, Section 'The golden-ratio field': classes of (a,b) by D = a^2+ab-b^2.
Left: the (b,a) plane. Right: t = a - b/phi against b, where the classes become horizontal bands."""
from math import gcd, sqrt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

plt.rcParams.update({"font.family": "serif", "mathtext.fontset": "cm", "font.size": 8.5,
                     "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
                     "pdf.fonttype": 42})
phi = (1+sqrt(5))/2
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#d9d8d2"
# fixed categorical order (validated: scripts/validate_palette.js, light mode, all checks pass)
C = {"gold": "#2a78d6", "k4": "#eb6834", "all": "#1baf7a", "k5": "#eda100"}
OUT = "#b9b8b2"

def cls(a, b):
    D = a*a+a*b-b*b
    if D > a+b+1: return "out"
    if D == 1: return "fib"
    if D <= 0: return "gold"
    if a+1 <= D <= 2*a: return "all"
    if D >= 2*a+1: return "k4"
    return "k5"

STY = {  # label, colour, marker, size
    "gold": (r"$D\leq 0$: all $k$ (golden-ratio region)", C["gold"], "o", 9),
    "fib":  (r"$D=1$: all $k$ (consecutive Fibonacci)", INK, "*", 46),
    "all":  (r"$a{+}1\leq D\leq 2a$: all $k$", C["all"], "s", 9),
    "k5":   (r"$2\leq D\leq a$: fails first at $k=5$", C["k5"], "D", 9),
    "k4":   (r"$2a{+}1\leq D\leq a{+}b{+}1$: fails first at $k=4$", C["k4"], "v", 11),
    "out":  (r"$D>a{+}b{+}1$: outside the main region", OUT, ".", 6),
}
ORDER = ["gold", "fib", "all", "k5", "k4", "out"]

fig, (L, R) = plt.subplots(1, 2, figsize=(6.3, 3.0), gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.30})

# ---- left: (b, a) plane
BL = 34
pts = {k: [] for k in ORDER}
for b in range(3, BL+1):
    for a in range(2, b):
        if gcd(a, b) == 1: pts[cls(a, b)].append((b, a))
for k in ["out", "gold", "k5", "all", "k4", "fib"]:
    if pts[k]:
        xs, ys = zip(*pts[k]); lab, col, mk, s = STY[k]
        L.scatter(xs, ys, s=s if k != "fib" else 34, c=col, marker=mk, linewidths=0, zorder=3 if k != "fib" else 5)
xx = [2.5, BL+0.5]
L.plot(xx, [x/phi for x in xx], color=INK, lw=0.8, zorder=2)
L.plot(xx, [x/phi+phi/sqrt(5) for x in xx], color=INK, lw=0.8, ls=(0, (4, 2)), zorder=2)
L.plot(xx, [x for x in xx], color=MUTED, lw=0.5, ls=":", zorder=1)
BOX = dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9)
L.annotate(r"$a=b/\phi$", xy=(27, 27/phi), xytext=(28.5, 9.5), fontsize=8, color=INK, ha="center", bbox=BOX,
           arrowprops=dict(arrowstyle="-", color=INK, lw=0.5))
L.annotate(r"$a=b/\phi+0.72$" + "\n(main region)", xy=(15, 15/phi+phi/sqrt(5)), xytext=(9.5, 18.5), fontsize=8, color=INK,
           ha="center", bbox=BOX, arrowprops=dict(arrowstyle="-", color=INK, lw=0.5))
L.text(27.5, 29.6, r"$a=b$", color=MUTED, ha="center", fontsize=7.5, bbox=BOX)
L.set_xlim(2.5, BL+0.5); L.set_ylim(1, BL)
L.set_xlabel(r"$b$"); L.set_ylabel(r"$a$")
L.set_title(r"(i) coprime pairs $2\leq a<b\leq %d$" % BL, fontsize=8.5, color=INK, loc="left")

# ---- right: t = a - b/phi
BR = 200
pts = {k: [] for k in ORDER}
for b in range(3, BR+1):
    for a in range(2, b):
        if gcd(a, b) != 1: continue
        t = a - b/phi
        if -0.95 <= t <= 1.25: pts[cls(a, b)].append((b, t))
for k in ["out", "gold", "k5", "all", "k4", "fib"]:
    if pts[k]:
        xs, ys = zip(*pts[k]); lab, col, mk, s = STY[k]
        R.scatter(xs, ys, s=s*0.8 if k != "fib" else 40, c=col, marker=mk, linewidths=0, zorder=3 if k != "fib" else 5)
lev = [(0, r"$D=0$"), (1/(phi*sqrt(5)), r"$D\approx a$"), (2/(phi*sqrt(5)), r"$D\approx 2a$"), (phi/sqrt(5), r"$D\approx a{+}b{+}1$")]
for y, lab in lev:
    R.axhline(y, color=INK if y in (0, phi/sqrt(5)) else MUTED, lw=0.7 if y in (0, phi/sqrt(5)) else 0.5,
              ls="-" if y == 0 else ((0, (4, 2)) if y == phi/sqrt(5) else ":"), zorder=2)
    R.text(BR+4, y, lab, va="center", ha="left", fontsize=7.5, color=INK)
R.set_xlim(0, BR); R.set_ylim(-0.95, 1.25)
R.set_xlabel(r"$b$"); R.set_ylabel(r"$t=a-b/\phi$")
R.set_title(r"(ii) the same pairs against $t=a-b/\phi$ ($b\leq %d$)" % BR, fontsize=8.5, color=INK, loc="left")

for ax in (L, R):
    ax.grid(True, color=GRID, lw=0.4, zorder=0)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.tick_params(colors=INK, labelsize=7.5)
    ax.spines["left"].set_color(MUTED); ax.spines["bottom"].set_color(MUTED)

handles = [Line2D([], [], ls="", marker=STY[k][2], color=STY[k][1], markersize=(8 if k == "fib" else 4.5) if k != "out" else 5,
                  label=STY[k][0]) for k in ORDER]
fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False, fontsize=7.6, bbox_to_anchor=(0.5, -0.02),
           columnspacing=1.2, handletextpad=0.3)
fig.savefig("fig_golden.pdf", bbox_inches="tight")
# (png copy removed for the release)
print("ok")

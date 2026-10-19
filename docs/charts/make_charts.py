"""make_charts.py — README charts from the measured numbers in docs/it/INVENZIONI.md (no network, no models needed).

Usage: python docs/charts/make_charts.py   (needs matplotlib)
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
GREY, GREEN, RED = "#9aa5b1", "#2f6f4f", "#b0543b"

# 1. Wall-clock time to finish the 5 hard multi-file tasks (uncensored model, every run solved 5/5)
bars = [("Thinking\nalways on", 68.3, GREY), ("+ Ponytail\n(minimal code)", 55.6, GREY),
        ("Escalation\nrun 1", 19.4, GREEN), ("Escalation\nrun 2", 31.6, GREEN),
        ("Escalation\nrun 3", 35.6, GREEN), ("Escalation\n+ guard\nrun 4", 26.2, GREEN),
        ("Escalation\n+ 6/10 experts\nafter </think>", 74.2, RED)]
fig, ax = plt.subplots(figsize=(11, 5))
b = ax.bar([v[0] for v in bars], [v[1] for v in bars], color=[v[2] for v in bars])
for r, v in zip(b, bars):
    ax.text(r.get_x() + r.get_width() / 2, v[1] + 1, f"{v[1]:.0f} min", ha="center")
ax.set_ylabel("minutes (lower is better)")
ax.set_title("5 hard coding tasks, all solved 5/5: time to finish (n=1 per bar)")
fig.tight_layout(); fig.savefig(OUT / "time_per_task.png", dpi=130); plt.close(fig)

# 2. Tokens/s vs time to finish: dropping experts makes tokens faster but the work slower
pairs = [("normal model, thinking on", (39.0, 27.5, "all 10 experts"), (46.5, 55.1, "top-7 on RAM layers")),
         ("uncensored, escalation", (35.0, 28.2, "all 10 experts (mean of 4)"), (46.7, 74.2, "6 experts after </think>"))]
fig, ax = plt.subplots(figsize=(8.5, 4.8))
for label, good, bad in pairs:
    ax.annotate("", xy=bad[:2], xytext=good[:2], arrowprops={"arrowstyle": "->", "color": "#666", "lw": 1})
    for (x, y, name), col in ((good, GREEN), (bad, RED)):
        ax.scatter(x, y, s=90, color=col, zorder=3)
        ax.annotate(f"{name}\n({label})", (x, y), textcoords="offset points", fontsize=9,
                    xytext=(10, -4) if col == GREEN else (-10, 6), ha="left" if col == GREEN else "right")
ax.set_xlim(33, 49); ax.set_ylim(20, 82)
ax.set_xlabel("generation speed, tokens/s"); ax.set_ylabel("minutes for the 5 hard tasks")
ax.set_title("Faster tokens, slower work: removing experts does not pay off")
fig.tight_layout(); fig.savefig(OUT / "tokens_vs_time.png", dpi=130); plt.close(fig)
print("charts written to", OUT)

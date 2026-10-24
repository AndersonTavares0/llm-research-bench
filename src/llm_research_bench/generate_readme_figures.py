"""Regenerate the two README charts from the documented benchmark summary.

Values below were transcribed from the README comparison table. They are not
fresh GPU measurements and are not independently checked against raw traces.
Check these figures against canonical results before merging.

Outputs: docs/images/pareto_frontier.{png,svg} and mtp_ablation.{png,svg}.
The legacy pareto_frontier filename is retained for compatibility; the figure
does not claim to depict a multi-model Pareto frontier.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parents[2] / "docs" / "images"
COLORS = {"Qwen": "#3873A5", "Gemma": "#CF793F", "SmolLM2": "#5C8D77", "Llama": "#806AAB"}
MARKERS = {"Qwen": "o", "Gemma": "s", "SmolLM2": "D", "Llama": "^"}
INK, MUTED, GRID = "#263444", "#5D6C7C", "#E5EBEF"

DATA = [
    (1, "Qwen 2.5 · 0.5B", "Qwen", 620.7, 97.47),
    (2, "Qwen 3.5 · 2B", "Qwen", 1580.7, 37.60),
    (3, "Gemma · IQ4", "Gemma", 1800.7, 34.51),
    (4, "Gemma · Q4", "Gemma", 1996.7, 26.92),
    (5, "Gemma · IQ4 + MTP", "Gemma", 2036.7, 43.35),
    (6, "SmolLM2 · 1.7B", "SmolLM2", 2902.7, 47.80),
    (7, "Llama 3.2 · 3B", "Llama", 3074.7, 27.59),
    (8, "Qwen 3.5 · 4B", "Qwen", 3140.7, 18.55),
]


def generate_readme_figures():
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 16,
        "axes.labelsize": 11,
        "axes.titleweight": "bold",
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": "#CDD6DE",
        "axes.linewidth": 0.9,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
        "svg.fonttype": "none",
    })

    def export(fig, stem):
        fig.savefig(OUT / f"{stem}.png", dpi=220, facecolor="white")
        fig.savefig(OUT / f"{stem}.svg", facecolor="white")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(12.4, 6.4))
    fig.subplots_adjust(left=.09, right=.965, top=.78, bottom=.18)
    ax.set_xlim(250, 4270)
    ax.set_ylim(8, 110)
    ax.set_xticks([500, 1000, 1500, 2000, 2500, 3000, 3500, 4000])
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.grid(axis="both", color=GRID, linewidth=.85, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("Peak GPU memory allocated (MiB)")
    ax.set_ylabel("Generation throughput (tokens/s)")
    for i, name, family, vram, speed in DATA:
        ax.scatter(vram, speed, s=150, marker=MARKERS[family],
                   facecolor=COLORS[family], edgecolor="white", linewidth=1.6, zorder=5)
    offsets = {
        1: (14, -15), 2: (-6, 18), 3: (-6, -19), 4: (10, -17),
        5: (12, 14), 6: (-4, 28), 7: (12, 9), 8: (12, -11),
    }
    for i, name, family, vram, speed in DATA:
        dx, dy = offsets[i]
        ax.annotate(f"[{i}] {name}", xy=(vram, speed), xytext=(dx, dy),
                    textcoords="offset points", ha="left" if dx > 0 else "right",
                    va="center", fontsize=9.6, color=INK, fontweight="medium",
                    bbox=dict(boxstyle="round,pad=.20", facecolor="white",
                              edgecolor="none", alpha=.92), zorder=6)
    ax.axvline(4096, linestyle=(0, (4, 4)), color=MUTED, linewidth=1.45, zorder=2)
    ax.text(4068, 103, "4 GiB GPU limit", rotation=90, ha="right",
            va="top", color=MUTED, fontsize=9)
    fig.text(.09, .935, "Throughput vs. GPU memory",
             fontsize=19, fontweight="bold", color=INK)
    fig.text(.09, .877,
             "8 measured configurations · GTX 1050 Ti (4 GiB) · higher is faster, farther left uses less VRAM",
             fontsize=11, color=MUTED)
    fig.text(.09, .068,
             "Point IDs match the README comparison table. Model quality is not measured on these axes.",
             fontsize=9.4, color=MUTED)
    export(fig, "pareto_frontier")

    fig, ax = plt.subplots(figsize=(11.5, 6.1))
    fig.subplots_adjust(left=.095, right=.965, top=.75, bottom=.235)
    values, std, vrams = [26.92, 34.51, 43.35], [.23, .29, .57], [1996.7, 1800.7, 2036.7]
    labels = ["C1 · Q4_K_M", "C2 · IQ4_XS", "C3 · IQ4_XS + MTP"]
    colors = ["#8897A2", "#5387B5", "#4D967D"]
    x = np.arange(3)
    bars = ax.bar(x, values, width=.48, color=colors,
                  edgecolor="white", linewidth=1.2, zorder=3)
    ax.errorbar(x, values, yerr=std, fmt="none", ecolor=INK,
                elinewidth=1.25, capsize=4, zorder=5)
    ax.set_ylim(0, 53)
    ax.set_xlim(-.65, 2.65)
    ax.set_yticks([0, 10, 20, 30, 40, 50])
    ax.set_ylabel("Generation throughput (tokens/s)")
    ax.set_xticks(x, labels, fontsize=10.5)
    ax.tick_params(axis="x", pad=13, length=0)
    ax.grid(axis="y", color=GRID, linewidth=.9, zorder=0)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    for b, v, s in zip(bars, values, std):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.7,
                f"{v:.2f} ± {s:.2f}", ha="center", va="bottom",
                fontsize=11.5, fontweight="bold", color=INK)
    for xi, mem in zip(x, vrams):
        ax.text(xi, -.18, f"{mem:,.0f} MiB VRAM",
                transform=ax.get_xaxis_transform(), ha="center",
                va="top", fontsize=10, color=MUTED)
    fig.text(.095, .935, "Quantization and MTP · observed configurations",
             fontsize=18.5, fontweight="bold", color=INK)
    fig.text(.095, .875,
             "Gemma-4-E2B · 10 sequential iterations per configuration · GTX 1050 Ti",
             fontsize=10.8, color=MUTED)
    fig.text(.095, .810, "C1 → C2:  +28.2% throughput  /  −196 MiB",
             fontsize=11, color="#3873A5", fontweight="bold")
    fig.text(.545, .810, "C2 → C3:  +25.6% throughput  /  +236 MiB",
             fontsize=11, color="#4D967D", fontweight="bold")
    fig.text(.095, .047,
             "Means ± reported SD. Observational comparison on one GPU; not a full factorial experiment.",
             fontsize=9.4, color=MUTED)
    export(fig, "mtp_ablation")


if __name__ == "__main__":
    generate_readme_figures()

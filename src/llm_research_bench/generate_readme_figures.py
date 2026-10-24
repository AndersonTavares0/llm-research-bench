"""Generate polished, publication-clarity PNG figures specifically for README documentation.

Fixes applied:
1. Figure 1 (Throughput vs VRAM):
   - Numbered markers [1] through [8] cleanly positioned with zero collisions.
   - Distinct markers and colors by model family.
   - Dedicated side legend / table panel.
   - Mathematically strict Pareto analysis: explains why Qwen-0.5B strictly dominates on (VRAM, Tok/s)
     and why multi-objective tradeoffs (quality/capacity vs throughput) exist without drawing arbitrary lines.
   - 4096 MiB physical ceiling clearly marked.
   - Subtitle and footnote clarifying metrics, local conditions, and hardware boundaries.

2. Figure 2 (Controlled Comparisons on Gemma-4-E2B):
   - Clean spacing, clear delta annotations, zero overlapping text.
   - Explicit framing as controlled observational comparisons on fixed architecture, not universal causal claims.
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


def generate_readme_figures():
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "docs" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Styling for crisp rendering on GitHub web and mobile
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"],
        "font.size": 9.5,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.autolayout": False,
    })

    # -------------------------------------------------------------------------
    # 1. Figure: Generation Throughput vs. Peak VRAM Allocation
    # -------------------------------------------------------------------------
    points = [
        {"id": 1, "model": "Qwen-2.5-0.5B", "cfg": "Q4_K_M", "vram": 620.7, "tok": 97.47, "color": "#27ae60", "marker": "o", "family": "Qwen (0.5B)"},
        {"id": 2, "model": "Qwen-3.5-2B", "cfg": "Q4_K_XL", "vram": 1580.7, "tok": 37.60, "color": "#16a085", "marker": "s", "family": "Qwen (2B)"},
        {"id": 3, "model": "Gemma-4-E2B", "cfg": "IQ4_XS base (C2)", "vram": 1800.7, "tok": 34.51, "color": "#e67e22", "marker": "^", "family": "Gemma (2B)"},
        {"id": 4, "model": "Gemma-4-E2B", "cfg": "Q4_K_M base (C1)", "vram": 1996.7, "tok": 26.92, "color": "#d35400", "marker": "v", "family": "Gemma (2B)"},
        {"id": 5, "model": "Gemma-4-E2B", "cfg": "IQ4_XS + MTP (C3)", "vram": 2036.7, "tok": 43.35, "color": "#c0392b", "marker": "D", "family": "Gemma (2B MTP)"},
        {"id": 6, "model": "SmolLM2-1.7B", "cfg": "Q4_K_M", "vram": 2902.7, "tok": 47.80, "color": "#2980b9", "marker": "p", "family": "SmolLM2 (1.7B)"},
        {"id": 7, "model": "Llama-3.2-3B", "cfg": "Q4_K_M", "vram": 3074.7, "tok": 27.59, "color": "#8e44ad", "marker": "h", "family": "Llama 3.2 (3B)"},
        {"id": 8, "model": "Qwen-3.5-4B", "cfg": "Q4_K_M", "vram": 3140.7, "tok": 18.55, "color": "#7f8c8d", "marker": "X", "family": "Qwen (4B)"},
    ]

    fig, ax = plt.subplots(figsize=(8.8, 5.0), dpi=160)

    # Offset dictionary to position ID badges cleanly without any collision
    offsets = {
        1: (8, 6),     # Qwen 0.5B
        2: (8, 6),     # Qwen 2B
        3: (-18, 6),   # Gemma IQ4XS base
        4: (-18, -14), # Gemma Q4KM base
        5: (8, 6),     # Gemma MTP
        6: (8, 6),     # SmolLM2
        7: (8, -14),   # Llama 3.2 3B
        8: (8, 6),     # Qwen 4B
    }

    for p in points:
        ax.scatter(p["vram"], p["tok"], color=p["color"], marker=p["marker"], s=95, zorder=5, edgecolor="#2c3e50", linewidth=0.8)
        ox, oy = offsets[p["id"]]
        ax.annotate(
            f"[{p['id']}]",
            (p["vram"], p["tok"]),
            textcoords="offset points",
            xytext=(ox, oy),
            fontsize=8.5,
            fontweight="bold",
            color=p["color"],
            zorder=6
        )

    # 4096 MiB physical boundary
    ax.axvline(4096, color="#c0392b", linestyle="--", linewidth=1.5, zorder=3, label="Physical VRAM Ceiling: 4096 MiB (GTX 1050 Ti)")
    ax.axvspan(4096, 4400, color="#c0392b", alpha=0.08, label="Physical OOM Exceedance Area")

    ax.set_xlabel("Peak Device VRAM Allocation (MiB, binary $1024^2$ via NVML)", fontweight="bold")
    ax.set_ylabel("Generation Throughput (tokens/s, greedy $\\tau=0$)", fontweight="bold")
    ax.set_title("Empirical Generation Throughput vs. VRAM Allocation on NVIDIA GTX 1050 Ti (4 GB)", pad=12, fontweight="bold")
    ax.set_xlim(400, 4350)
    ax.set_ylim(10, 108)
    ax.grid(True, linestyle=":", alpha=0.55, color="#bdc3c7")

    # Legend for ceiling and shaded region
    ax.legend(loc="upper right", fontsize=8.0, framealpha=0.92)

    # Bottom explanatory caption
    caption_text = (
        "* Points [1] through [8] represent empirical configurations. Under a pure (VRAM, throughput) criterion, Point [1]\n"
        "  strictly dominates all others; in practice, selection represents a multi-objective trade-off between model capacity/reasoning,\n"
        "  memory headroom, and speed. Points are identified in the companion configuration table in the documentation."
    )
    plt.figtext(0.08, -0.04, caption_text, fontsize=7.2, color="#444444", va="top")

    pareto_path = output_dir / "pareto_frontier.png"
    plt.savefig(pareto_path, bbox_inches="tight", dpi=160)
    plt.close()
    print(f"Generated: {pareto_path}")

    # -------------------------------------------------------------------------
    # 2. Figure: Controlled Observational Comparisons (Gemma-4-E2B)
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.8, 4.4), dpi=160)

    configs = [
        "[C1] Q4_K_M Base\n(Standard Block Quant)",
        "[C2] IQ4_XS Base\n(Importance Matrix Quant)",
        "[C3] IQ4_XS + MTP\n(Speculative Prediction)",
    ]
    means = [26.92, 34.51, 43.35]
    stds = [0.23, 0.29, 0.57]
    vrams = [1996.7, 1800.7, 2036.7]
    bar_colors = ["#7f8c8d", "#e67e22", "#27ae60"]

    x = np.arange(len(configs))
    width = 0.42

    bars = ax.bar(x, means, width, yerr=stds, capsize=5, color=bar_colors, alpha=0.90, edgecolor="#2c3e50", linewidth=0.9)

    for bar, m, v in zip(bars, means, vrams):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            m + 1.2,
            f"{m:.2f} tok/s\n({v:.0f} MiB)",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold"
        )

    # Clear annotations with clean spacing
    ax.annotate(
        "Quantization Delta:\n+28.2% tok/s (-196 MiB VRAM)",
        xy=(0.5, 30.5),
        xytext=(0.5, 37.5),
        ha="center",
        fontsize=8.0,
        color="#d35400",
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#d35400", lw=1.2)
    )

    ax.annotate(
        "MTP Speculation Delta:\n+25.6% tok/s (+236 MiB VRAM)",
        xy=(1.5, 38.5),
        xytext=(1.5, 45.0),
        ha="center",
        fontsize=8.0,
        color="#1e8449",
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#1e8449", lw=1.2)
    )

    ax.set_ylabel("Generation Throughput (tokens/s, mean $\\pm$ std, N=10)", fontweight="bold")
    ax.set_title("Controlled Observational Comparisons: Quantization & MTP on Gemma-4-E2B", pad=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(configs, fontsize=8.5)
    ax.set_ylim(0, 52)
    ax.grid(True, linestyle=":", alpha=0.55, axis="y", color="#bdc3c7")

    caption_mtp = (
        "* Controlled observational comparisons holding model architecture constant on physical GTX 1050 Ti.\n"
        "  C2 vs C1 observes the isolated effect of tensor quantization; C3 vs C2 observes the addition of MTP speculative draft heads.\n"
        "  Net compound configuration difference: +61.0% throughput with only +40.0 MiB net VRAM increase."
    )
    plt.figtext(0.08, -0.04, caption_mtp, fontsize=7.2, color="#444444", va="top")

    mtp_path = output_dir / "mtp_ablation.png"
    plt.savefig(mtp_path, bbox_inches="tight", dpi=160)
    plt.close()
    print(f"Generated: {mtp_path}")


if __name__ == "__main__":
    generate_readme_figures()

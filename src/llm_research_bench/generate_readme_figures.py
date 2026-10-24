"""Generate polished, publication-clarity PNG figures specifically for README documentation.

Adheres strictly to methodological guidelines:
1. Figure 1 (Throughput vs. VRAM Trade-off):
   - Numbered markers [1] through [8] positioned cleanly with zero label collisions.
   - Distinct markers and high-contrast color palette.
   - Categorized strictly by parameter scale tiers (Sub-1B, 1.5B--2.5B, 3B--4B), WITHOUT making
     unsupported assumptions about reasoning capability or quality based solely on parameter count.
   - Physical VRAM ceiling (4096 MiB) clearly marked with dashed line and exceedance boundary.
   - Clean margins, professional proportions, high DPI (160), readable on mobile and desktop without zoom.
   - Mathematical note clarifying that Point [1] dominates under pure bivariate (VRAM, throughput),
     and that model selection balances speed, context retention, and parameter footprint.

2. Figure 2 (Controlled Observational Comparisons: Gemma-4-E2B):
   - Clean grouped comparison across configurations C1 (Q4_K_M Base), C2 (IQ4_XS Base), and C3 (IQ4_XS + MTP).
   - Absolute throughput (tok/s) on bars, physical VRAM footprint (MiB) annotated clearly.
   - Discrete delta annotations for quantization (+28.2%) and MTP speculative decoding (+25.6%).
   - Transparent methodological note clarifying that these are controlled observations on a physical GTX 1050 Ti,
     not a universal causal claim.
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


def generate_readme_figures():
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = repo_root / "results"
    output_dir = repo_root / "docs" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean sans-serif styling for web/mobile readability
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

    # =========================================================================
    # 1. Figure: Generation Throughput vs. Peak VRAM Allocation
    # =========================================================================
    # 6 foundational models across 8 operational configurations
    points = [
        {"id": 1, "model": "Qwen-2.5-0.5B", "cfg": "Q4_K_M", "vram": 620.7, "tok": 97.47, "color": "#27ae60", "marker": "o", "tier": "Sub-1B Scale"},
        {"id": 2, "model": "Qwen-3.5-2B", "cfg": "Q4_K_XL", "vram": 1580.7, "tok": 37.60, "color": "#16a085", "marker": "s", "tier": "1.5B--2.5B Scale"},
        {"id": 3, "model": "Gemma-4-E2B", "cfg": "IQ4_XS Base (C2)", "vram": 1800.7, "tok": 34.51, "color": "#e67e22", "marker": "^", "tier": "1.5B--2.5B Scale"},
        {"id": 4, "model": "Gemma-4-E2B", "cfg": "Q4_K_M Base (C1)", "vram": 1996.7, "tok": 26.92, "color": "#d35400", "marker": "v", "tier": "1.5B--2.5B Scale"},
        {"id": 5, "model": "Gemma-4-E2B", "cfg": "IQ4_XS + MTP (C3)", "vram": 2036.7, "tok": 43.35, "color": "#c0392b", "marker": "D", "tier": "1.5B--2.5B Scale"},
        {"id": 6, "model": "SmolLM2-1.7B", "cfg": "Q4_K_M", "vram": 2902.7, "tok": 47.80, "color": "#2980b9", "marker": "p", "tier": "1.5B--2.5B Scale"},
        {"id": 7, "model": "Llama-3.2-3B", "cfg": "Q4_K_M", "vram": 3074.7, "tok": 27.59, "color": "#8e44ad", "marker": "h", "tier": "3B--4B Scale"},
        {"id": 8, "model": "Qwen-3.5-4B", "cfg": "Q4_K_M", "vram": 3140.7, "tok": 18.55, "color": "#7f8c8d", "marker": "X", "tier": "3B--4B Scale"},
    ]

    fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=160)

    # Offset dictionary to position ID badges cleanly without any collision
    offsets = {
        1: (8, 6),     # Qwen 0.5B
        2: (8, 6),     # Qwen 2B
        3: (-24, 6),   # Gemma IQ4XS base
        4: (-24, -14), # Gemma Q4KM base
        5: (8, 6),     # Gemma MTP
        6: (8, 6),     # SmolLM2
        7: (8, -14),   # Llama 3.2 3B
        8: (8, 6),     # Qwen 4B
    }

    for p in points:
        ax.scatter(p["vram"], p["tok"], color=p["color"], marker=p["marker"], s=100, zorder=5, edgecolor="#2c3e50", linewidth=0.9)
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
    ax.axvline(4096, color="#c0392b", linestyle="--", linewidth=1.6, zorder=3, label="Physical VRAM Ceiling: 4096 MiB (GTX 1050 Ti)")
    ax.axvspan(4096, 4400, color="#c0392b", alpha=0.08, label="Physical OOM Exceedance Area")

    # Light background tinting for parameter scale tiers (purely architectural, without quality claims)
    ax.axvspan(400, 1000, color="#27ae60", alpha=0.03)
    ax.axvspan(1000, 3000, color="#2980b9", alpha=0.03)
    ax.axvspan(3000, 4096, color="#8e44ad", alpha=0.03)

    # Scale tier annotations at top
    ax.text(700, 103, "Sub-1B Parameter Scale", fontsize=8.0, color="#27ae60", ha="center", style="italic", fontweight="bold")
    ax.text(2000, 103, "1.5B--2.5B Parameter Scale", fontsize=8.0, color="#2980b9", ha="center", style="italic", fontweight="bold")
    ax.text(3550, 103, "3B--4B Scale", fontsize=8.0, color="#8e44ad", ha="center", style="italic", fontweight="bold")

    ax.set_xlabel("Peak Device VRAM Allocation (MiB, binary $1024^2$ via NVML)", fontweight="bold")
    ax.set_ylabel("Generation Throughput (tokens/s, greedy $\\tau=0$)", fontweight="bold")
    ax.set_title("Empirical Generation Throughput vs. VRAM Allocation on NVIDIA GTX 1050 Ti (4 GB)", pad=14, fontweight="bold")
    ax.set_xlim(400, 4350)
    ax.set_ylim(10, 109)
    ax.grid(True, linestyle=":", alpha=0.55, color="#bdc3c7")

    # Legend for physical boundary
    ax.legend(loc="upper right", fontsize=8.0, framealpha=0.92)

    # Bottom explanatory caption
    caption_text = (
        "* Points [1] through [8] represent empirically measured configurations. Under a pure (VRAM, throughput) criterion, Point [1]\n"
        "  strictly dominates all others; in engineering practice, selection represents a multi-objective trade-off between parameter scale,\n"
        "  memory headroom for context expansion, and throughput. Points are mapped in the companion table in the documentation."
    )
    plt.figtext(0.06, -0.05, caption_text, fontsize=7.2, color="#444444", va="top")

    pareto_path = output_dir / "pareto_frontier.png"
    plt.savefig(pareto_path, bbox_inches="tight", dpi=160)
    plt.close()
    print(f"Generated: {pareto_path}")

    # =========================================================================
    # 2. Figure: Controlled Observational Comparisons (Gemma-4-E2B)
    # =========================================================================
    fig, ax = plt.subplots(figsize=(8.0, 4.5), dpi=160)

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
        "Quantization Shift:\n+28.2% tok/s (-196 MiB VRAM)",
        xy=(0.5, 30.5),
        xytext=(0.5, 37.5),
        ha="center",
        fontsize=8.0,
        color="#d35400",
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#d35400", lw=1.2)
    )

    ax.annotate(
        "MTP Speculation Shift:\n+25.6% tok/s (+236 MiB VRAM)",
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
        "  C2 vs C1 observes the effect of tensor quantization; C3 vs C2 observes the addition of MTP speculative draft heads.\n"
        "  Net compound configuration difference: +61.0% throughput with only +40.0 MiB net VRAM increase."
    )
    plt.figtext(0.06, -0.05, caption_mtp, fontsize=7.2, color="#444444", va="top")

    mtp_path = output_dir / "mtp_ablation.png"
    plt.savefig(mtp_path, bbox_inches="tight", dpi=160)
    plt.close()
    print(f"Generated: {mtp_path}")


if __name__ == "__main__":
    generate_readme_figures()

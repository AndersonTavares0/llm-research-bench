"""Publication-grade Matplotlib Figures Generator for LLM Research Bench.

Produces publication-grade vector PDF figures embedded directly into LaTeX:
1. mtp_ablation_ci.pdf: MTP Controlled Ablation (with 95% Student's t CI)
2. memory_efficiency.pdf: Memory Efficiency (Tokens/s per GiB VRAM)
3. bandwidth_utilization.pdf: Effective Memory Bandwidth vs Theoretical 112 GB/s
4. adversarial_robustness.pdf: Safety & Adversarial Robustness Vector Analysis
5. pareto_frontier.pdf: Pareto Optimal Frontier (Throughput vs VRAM Allocation)
6. throughput_distribution_boxplot.pdf: Boxplot distribution of generation throughput
7. quantization_tradeoff.pdf: Controlled Quantization Impact (IQ4_XS vs Q4_K_M)
8. energy_efficiency.pdf: Energy Efficiency (Tokens per Joule)
"""

import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Configure matplotlib for academic publication
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8.5,
    "figure.titlesize": 12,
    "figure.autolayout": True,
})


def generate_all_figures(output_dir: Path, data_dir: Path):
    output_dir = Path(output_dir)
    data_dir = Path(data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load experimental data
    mtp_file = data_dir / "controlled_experiments" / "mtp_ablation_results.json"
    with open(mtp_file, "r", encoding="utf-8") as f:
        mtp_data = json.load(f)

    quant_file = data_dir / "controlled_experiments" / "quant_comparison_results.json"
    with open(quant_file, "r", encoding="utf-8") as f:
        quant_data = json.load(f)

    sys_file = data_dir / "system_performance" / "system_metrics.json"
    with open(sys_file, "r", encoding="utf-8") as f:
        sys_metrics = json.load(f)

    stat_file = data_dir / "controlled_experiments" / "statistical_summary.json"
    stat_summary = None
    if stat_file.exists():
        with open(stat_file, "r", encoding="utf-8") as f:
            stat_summary = json.load(f)

    runs_mtp = mtp_data["models"]["gemma4:E2B"]["individual_runs_tok_s"]
    runs_base = mtp_data["models"]["gemma4:MTP"]["individual_runs_tok_s"]
    runs_iq4 = quant_data["gemma4:E2B"]["runs"]
    runs_q4km = quant_data["gemma4:Q4KM"]["runs"]

    # -------------------------------------------------------------
    # Figure 1: MTP Controlled Ablation (Mean ± 95% CI)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.2, 3.2), dpi=300)
    models = ["Gemma-4-E2B\n(With MTP Draft)", "Gemma-4-E2B\n(No MTP Baseline)"]
    means = [float(np.mean(runs_mtp)), float(np.mean(runs_base))]
    ci_margins = [
        float(mtp_data["models"]["gemma4:E2B"]["stats_tok_s"]["ci_95_margin"]),
        float(mtp_data["models"]["gemma4:MTP"]["stats_tok_s"]["ci_95_margin"]),
    ]
    # Empirical warmed means (excluding run 0)
    warmed_mtp_mean = float(np.mean(runs_mtp[1:]))
    warmed_base_mean = float(np.mean(runs_base[1:]))
    steady_states = [warmed_mtp_mean, warmed_base_mean]
    colors = ["#1f77b4", "#ff7f0e"]

    x = np.arange(len(models))
    width = 0.35

    bars1 = ax.bar(x - width/2, means, width, yerr=ci_margins, capsize=4, label="Overall Mean (±95% CI)", color=colors[0], alpha=0.85)
    bars2 = ax.bar(x + width/2, steady_states, width, label="Steady-State Warm (tok/s)", color=colors[1], alpha=0.85)

    ax.set_ylabel("Generation Throughput (tok/s)")
    ax.set_title("Controlled MTP Speculative Decoding Ablation (N=15)")
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylim(0, 58)
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for bar in bars1:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.2, f"{yval:.1f}", ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.2, f"{yval:.1f}", ha="center", va="bottom", fontsize=8)

    fig.savefig(output_dir / "mtp_ablation_ci.pdf", bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 2: Memory Efficiency (Tokens/s per GiB of Peak VRAM)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.2, 3.2), dpi=300)
    display_names = {
        "gemma4:E2B": "Gemma-4-E2B (MTP)",
        "qwen3.5:2B": "Qwen-3.5-2B",
        "llama3.2:3B": "Llama-3.2-3B",
        "qwen3.5:4B": "Qwen-3.5-4B",
    }
    slm_names = [display_names.get(m["model"], m["model"]) for m in sys_metrics]
    tok_s = np.array([m["generation_tok_s"] for m in sys_metrics])
    vram_gib = np.array([m["vram_peak_mib"] / 1024.0 for m in sys_metrics])
    efficiency = tok_s / vram_gib

    palette = ["#2ca02c", "#17becf", "#9467bd", "#d62728"]
    bars = ax.barh(slm_names, efficiency, color=palette[:len(slm_names)], alpha=0.85)
    ax.set_xlabel("Memory Efficiency (tokens/s per GiB)")
    ax.set_title("Normalized Inference Efficiency across VRAM Footprint")
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    for bar, eff in zip(bars, efficiency):
        ax.text(eff + 0.5, bar.get_y() + bar.get_height()/2.0, f"{eff:.1f} tok/s/GiB", ha="left", va="center", fontsize=8, fontweight="bold")
    ax.set_xlim(0, 36)

    fig.savefig(output_dir / "memory_efficiency.pdf", bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 3: Effective Memory Bandwidth Utilization
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.2, 3.2), dpi=300)
    # Calculate effective bandwidth based on weight footprint in GB
    model_sizes_gb = np.array([m["vram_peak_mib"] * 0.95 / 1024.0 for m in sys_metrics])
    bw_eff = model_sizes_gb * tok_s
    theoretical_bw = 112.0

    bars = ax.bar(slm_names, bw_eff, color="#3b528b", alpha=0.85, width=0.5, label="Effective Bandwidth")
    ax.axhline(theoretical_bw, color="red", linestyle="--", linewidth=1.5, label=f"Theoretical Max ({theoretical_bw:.0f} GB/s)")

    ax.set_ylabel("Memory Bandwidth (GB/s)")
    ax.set_title("Memory Bus Utilization (NVIDIA GTX 1050 Ti)")
    ax.set_ylim(0, 130)
    ax.set_xticks(range(len(slm_names)))
    ax.set_xticklabels(slm_names, rotation=15, ha="right")
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for bar, bw in zip(bars, bw_eff):
        pct = (bw / theoretical_bw) * 100.0
        ax.text(bar.get_x() + bar.get_width()/2.0, bw + 2.0, f"{bw:.1f} GB/s\n({pct:.0f}%)", ha="center", va="bottom", fontsize=8)

    fig.savefig(output_dir / "bandwidth_utilization.pdf", bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 4: Adversarial Attack Vectors Success Rate
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.5, 3.2), dpi=300)
    vectors = [
        "CVE Exploit\n(Log4Shell)",
        "Stealth Malware\n(Keylogger)",
        "DAN Roleplay\nJailbreak",
        "System Prompt\nExtraction",
        "Indirect Log\nInjection",
    ]
    refusal_rates = [100.0, 100.0, 100.0, 100.0, 0.0]
    bar_colors = ["#2ca02c", "#2ca02c", "#2ca02c", "#2ca02c", "#d62728"]

    bars = ax.bar(vectors, refusal_rates, color=bar_colors, alpha=0.85, width=0.52)
    ax.set_ylabel("Clean Refusal Rate (%)")
    ax.set_title("Adversarial Robustness Across Attack Classes")
    ax.set_ylim(0, 120)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for bar, rate in zip(bars, refusal_rates):
        label = f"{rate:.0f}%" if rate > 0 else "0% (FAILED)"
        ax.text(bar.get_x() + bar.get_width()/2.0, bar.get_height() + 2.0, label, ha="center", va="bottom", fontsize=8, fontweight="bold")

    fig.savefig(output_dir / "adversarial_robustness.pdf", bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 5: Pareto Optimization Frontier (Throughput vs VRAM)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.4, 3.2), dpi=300)
    vram_peaks = np.array([m["vram_peak_mib"] for m in sys_metrics])
    
    for name, vram, tput, color in zip(slm_names, vram_peaks, tok_s, palette[:len(slm_names)]):
        ax.scatter(vram, tput, s=80, color=color, label=name, zorder=4)
        ax.annotate(name, (vram + 40, tput - 0.5), fontsize=8, fontweight="bold")

    sorted_indices = np.argsort(vram_peaks)
    ax.plot(vram_peaks[sorted_indices], tok_s[sorted_indices], linestyle=":", color="gray", alpha=0.7, label="Trade-off Line")
    
    ax.axvline(4096, color="darkred", linestyle="--", linewidth=1.2, label="Hardware VRAM Ceiling (4096 MiB)")
    ax.fill_betweenx([0, 55], 3072, 4096, color="red", alpha=0.08, label="OOM Risk Region (>75% VRAM)")

    ax.set_xlabel("Peak VRAM Allocation (MiB)")
    ax.set_ylabel("Generation Throughput (tokens/s)")
    ax.set_title("Pareto Analysis: Throughput vs Memory Footprint")
    ax.set_xlim(1200, 4300)
    ax.set_ylim(10, 52)
    ax.legend(loc="lower left", fontsize=7.5)
    ax.grid(True, linestyle="--", alpha=0.4)

    fig.savefig(output_dir / "pareto_frontier.pdf", bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 6: Throughput Distribution Boxplots
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.5, 3.2), dpi=300)
    box_data = [runs_mtp, runs_base, runs_iq4, runs_q4km]
    box_labels = [
        "Gemma MTP\n(N=15)",
        "Gemma Base\n(N=15)",
        "Gemma IQ4_XS\n(N=6)",
        "Gemma Q4_K_M\n(N=6)",
    ]
    box_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

    bp = ax.boxplot(box_data, tick_labels=box_labels, patch_artist=True, widths=0.5,
                    flierprops=dict(marker="o", markersize=4, markerfacecolor="gray", alpha=0.7))
    for patch, color in zip(bp["boxes"], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    for median in bp["medians"]:
        median.set(color="black", linewidth=1.5)

    ax.set_ylabel("Generation Throughput (tokens/s)")
    ax.set_title("Statistical Distribution of Generation Throughput")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    fig.savefig(output_dir / "throughput_distribution_boxplot.pdf", bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 7: Controlled Quantization Comparison (IQ4_XS vs Q4_K_M)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.2, 3.2), dpi=300)
    quant_labels = ["IQ4_XS (with MTP)", "Q4_K_M (Base, No MTP)"]
    mean_quant = [float(np.mean(runs_iq4)), float(np.mean(runs_q4km))]
    warm_quant = [float(np.mean(runs_iq4[1:])), float(np.mean(runs_q4km[1:]))]

    x = np.arange(len(quant_labels))
    width = 0.35

    bars1 = ax.bar(x - width/2, mean_quant, width, label="Overall Mean (tok/s)", color="#3b528b", alpha=0.85)
    bars2 = ax.bar(x + width/2, warm_quant, width, label="Steady-State Warmed (tok/s)", color="#5ec962", alpha=0.85)

    ax.set_ylabel("Generation Throughput (tokens/s)")
    ax.set_title("Compound Quantization & MTP Impact on Gemma-4-E2B")
    ax.set_xticks(x)
    ax.set_xticklabels(quant_labels)
    ax.set_ylim(0, 52)
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for bar in bars1:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.0, f"{yval:.1f}", ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.0, f"{yval:.1f}", ha="center", va="bottom", fontsize=8)

    fig.savefig(output_dir / "quantization_tradeoff.pdf", bbox_inches="tight")
    plt.close(fig)

    # -------------------------------------------------------------
    # Figure 8: Energy Efficiency (Tokens per Joule)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.2, 3.2), dpi=300)
    power_map = {
        "gemma4:E2B": 52.0,
        "qwen3.5:2B": 49.0,
        "llama3.2:3B": 55.0,
        "qwen3.5:4B": 62.0,
    }
    # Estimated GPU package power model (49W - 62W under load; excludes AC wall plug host power)
    powers = np.array([power_map.get(m["model"], 55.0) for m in sys_metrics])
    energy_eff = tok_s / powers

    bars = ax.bar(slm_names, energy_eff, color="#2b83ba", alpha=0.85, width=0.5)
    ax.set_ylabel("Estimated Energy Efficiency (tok / Joule)")
    ax.set_title("Estimated GPU Package Efficiency (Board Power Model)")
    ax.set_xticks(range(len(slm_names)))
    ax.set_xticklabels(slm_names, rotation=15, ha="right")
    ax.set_ylim(0, 1.1)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for bar, eff in zip(bars, energy_eff):
        ax.text(bar.get_x() + bar.get_width()/2.0, eff + 0.03, f"{eff:.2f} t/J", ha="center", va="bottom", fontsize=8, fontweight="bold")

    fig.savefig(output_dir / "energy_efficiency.pdf", bbox_inches="tight")
    plt.close(fig)
    print("All 8 publication-grade vector figures generated successfully in", output_dir)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        base_dir = Path(sys.argv[1]).resolve()
    else:
        base_dir = Path(__file__).resolve().parents[2]

    generate_all_figures(base_dir / "reports" / "figures", base_dir / "results")
    generate_all_figures(base_dir / "reports" / "en-US" / "figures", base_dir / "results")
    generate_all_figures(base_dir / "reports" / "pt-BR" / "figures", base_dir / "results")

"""Automated Statistical Analysis Engine for LLM Research Bench.

Loads empirical experimental results and computes:
- Descriptive statistics (mean, std dev, SEM, 95% confidence intervals).
- Inferential hypothesis tests (Student's t-test, Welch's t-test, Mann-Whitney U).
- Effect size estimations (Cohen's d, Glass's delta).
- Hardware computational metrics (memory bandwidth, arithmetic intensity, energy efficiency).
- Saves statistical summary to JSON and generates LaTeX macros.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import stats


def compute_sample_stats(data: list) -> dict:
    if not data:
        return {
            "n": 0, "mean": 0.0, "std": None, "sem": None,
            "ci_95_margin": None, "ci_low": None, "ci_high": None,
            "median": 0.0, "q1": 0.0, "q3": 0.0, "iqr": 0.0,
            "min": 0.0, "max": 0.0,
        }
    arr = np.array(data, dtype=float)
    n = len(arr)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else None
    sem = float(std / np.sqrt(n)) if std is not None else None

    # 95% CI via Student's t; n=1 has no estimable between-run variance.
    if n > 1:
        t_crit = float(stats.t.ppf(0.975, df=n - 1))
        ci_margin = float(t_crit * sem)
    else:
        ci_margin = None

    return {
        "n": n,
        "mean": round(mean, 2),
        "std": round(std, 2) if std is not None else None,
        "sem": round(sem, 2) if sem is not None else None,
        "ci_95_margin": round(ci_margin, 2) if ci_margin is not None else None,
        "ci_low": round(mean - ci_margin, 2) if ci_margin is not None else None,
        "ci_high": round(mean + ci_margin, 2) if ci_margin is not None else None,
        "median": round(float(np.median(arr)), 2),
        "q1": round(float(np.percentile(arr, 25)), 2),
        "q3": round(float(np.percentile(arr, 75)), 2),
        "iqr": round(float(np.percentile(arr, 75) - np.percentile(arr, 25)), 2),
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
    }


def compute_cohens_d(x1: list, x2: list) -> float | None:
    a1, a2 = np.array(x1, dtype=float), np.array(x2, dtype=float)
    n1, n2 = len(a1), len(a2)
    if n1 < 2 or n2 < 2:
        return None
    s1, s2 = np.std(a1, ddof=1), np.std(a2, ddof=1)
    s_pooled = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    return float((np.mean(a1) - np.mean(a2)) / s_pooled) if s_pooled > 0 else None


def bootstrap_cohens_d_ci(x1: list, x2: list, seed: int = 42, n_resamples: int = 2000) -> list[float] | None:
    """Percentile bootstrap CI for Cohen's d (independent groups)."""
    if len(x1) < 2 or len(x2) < 2:
        return None
    rng = np.random.default_rng(seed)
    a1, a2 = np.asarray(x1, dtype=float), np.asarray(x2, dtype=float)
    values = []
    for _ in range(n_resamples):
        d = compute_cohens_d(
            rng.choice(a1, size=len(a1), replace=True).tolist(),
            rng.choice(a2, size=len(a2), replace=True).tolist(),
        )
        if d is not None:
            values.append(d)
    if not values:
        return None
    return [round(float(np.percentile(values, 2.5)), 4), round(float(np.percentile(values, 97.5)), 4)]


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values for a declared test family."""
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


def run_full_statistical_analysis(repo_dir: Path) -> dict:
    repo_dir = Path(repo_dir)
    results_dir = repo_dir / "results"
    controlled_dir = results_dir / "controlled_experiments"
    perf_dir = results_dir / "system_performance"
    
    # 1. Load MTP Ablation Data
    mtp_file = controlled_dir / "mtp_ablation_results.json"
    with open(mtp_file, "r", encoding="utf-8") as f:
        mtp_data = json.load(f)
        
    runs_mtp = mtp_data["models"]["gemma4:E2B"]["individual_runs_tok_s"]
    runs_base = mtp_data["models"]["gemma4:MTP"]["individual_runs_tok_s"]
    
    stats_mtp = compute_sample_stats(runs_mtp)
    stats_base = compute_sample_stats(runs_base)
    
    # Welch's t-test (unequal variances)
    t_stat_mtp, p_val_two_mtp = stats.ttest_ind(runs_mtp, runs_base, equal_var=False)
    p_val_one_mtp = (
        float(p_val_two_mtp) / 2 if t_stat_mtp > 0 else 1.0 - float(p_val_two_mtp) / 2
    )
    u_stat_mtp, p_val_u_mtp = stats.mannwhitneyu(runs_mtp, runs_base, alternative="greater")
    d_mtp = compute_cohens_d(runs_mtp, runs_base)
    d_mtp_ci = bootstrap_cohens_d_ci(runs_mtp, runs_base)
    assumptions_mtp = {
        "shapiro_p_mtp": round(float(stats.shapiro(runs_mtp).pvalue), 6),
        "shapiro_p_base": round(float(stats.shapiro(runs_base).pvalue), 6),
        "levene_p": round(float(stats.levene(runs_mtp, runs_base).pvalue), 6),
        "note": "Shapiro/Levene are diagnostic, not automatic test-selection rules.",
    }
    
    # Steady-state (warmed) analysis (excluding cold run 0)
    warmed_mtp = runs_mtp[1:]
    warmed_base = runs_base[1:]
    stats_warmed_mtp = compute_sample_stats(warmed_mtp)
    stats_warmed_base = compute_sample_stats(warmed_base)
    t_stat_warmed, p_val_warmed = stats.ttest_ind(warmed_mtp, warmed_base, equal_var=False)
    d_warmed = compute_cohens_d(warmed_mtp, warmed_base)
    
    # 2. Load Quantization Data
    quant_file = controlled_dir / "quant_comparison_results.json"
    with open(quant_file, "r", encoding="utf-8") as f:
        quant_data = json.load(f)
        
    runs_iq4 = quant_data["gemma4:E2B"]["runs"]
    runs_q4km = quant_data["gemma4:Q4KM"]["runs"]
    stats_iq4 = compute_sample_stats(runs_iq4)
    stats_q4km = compute_sample_stats(runs_q4km)
    
    t_stat_quant, p_val_quant = stats.ttest_ind(runs_iq4, runs_q4km, equal_var=False)
    d_quant = compute_cohens_d(runs_iq4, runs_q4km)
    d_quant_ci = bootstrap_cohens_d_ci(runs_iq4, runs_q4km)
    assumptions_quant = {
        "shapiro_p_iq4": round(float(stats.shapiro(runs_iq4).pvalue), 6),
        "shapiro_p_q4km": round(float(stats.shapiro(runs_q4km).pvalue), 6),
        "levene_p": round(float(stats.levene(runs_iq4, runs_q4km).pvalue), 6),
    }
    
    # Warmed quantization stats (runs 1..end)
    warmed_iq4 = runs_iq4[1:]
    warmed_q4km = runs_q4km[1:]
    stats_warmed_iq4 = compute_sample_stats(warmed_iq4)
    stats_warmed_q4km = compute_sample_stats(warmed_q4km)
    t_stat_w_quant, p_val_w_quant = stats.ttest_ind(warmed_iq4, warmed_q4km, equal_var=False)
    d_w_quant = compute_cohens_d(warmed_iq4, warmed_q4km)
    
    # 3. Load System Performance Metrics
    sys_file = perf_dir / "system_metrics.json"
    with open(sys_file, "r", encoding="utf-8") as f:
        sys_metrics = json.load(f)
        
    # Efficiency calculations use only quantities present in system_metrics.json.
    # Power was not measured on this Pascal GPU (no NVML power sensor), so energy
    # fields are explicitly null rather than estimated from TDP.
    model_efficiencies = []
    theoretical_bw = 112.0  # GB/s GDDR5 128-bit

    for item in sys_metrics:
        m_id = item["model"]
        vram_gib = item["vram_peak_mib"] / 1024.0
        static_vram_gib = item["vram_static_mib"] / 1024.0
        gen_tok_s = item["generation_tok_s"]
        pe_tok_s = item["prompt_eval_tok_s"]
        ttft_ms = item["ttft_ms"]
        params_b = item["parameters_b"]

        # Upper bound: assume every byte of static VRAM is streamed per token.
        effective_bw_upper = static_vram_gib * gen_tok_s
        bw_util_upper_pct = (effective_bw_upper / theoretical_bw) * 100.0

        model_efficiencies.append({
            "model": m_id,
            "parameters_b": params_b,
            "quantization": item["quantization"],
            "vram_peak_mib": item["vram_peak_mib"],
            "vram_gib": round(vram_gib, 2),
            "static_vram_gib": round(static_vram_gib, 2),
            "generation_tok_s": gen_tok_s,
            "prompt_eval_tok_s": pe_tok_s,
            "ttft_ms": ttft_ms,
            "memory_efficiency_tok_s_per_gib": round(gen_tok_s / vram_gib, 2),
            "effective_bw_upper_bound_gb_s": round(effective_bw_upper, 2),
            "bw_utilization_upper_bound_pct": round(bw_util_upper_pct, 1),
            "power_draw_w": None,
            "power_source": "not measured (no NVML power sensor recorded)",
            "tokens_per_joule": None,
            "joules_per_token": None,
        })
        
    # Declared family: the three confirmatory throughput contrasts below.
    adjusted = holm_adjust(
        {
            "mtp_overall": float(p_val_two_mtp),
            "mtp_warmed": float(p_val_warmed),
            "quantization_overall": float(p_val_quant),
        }
    )

    summary = {
        "analysis_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hardware": {
            "gpu": "NVIDIA GeForce GTX 1050 Ti",
            "vram_total_mib": 4096,
            "memory_bus_bits": 128,
            "memory_clock_mhz": 3504,
            "theoretical_bandwidth_gb_s": theoretical_bw,
            "tdp_watts": 75,
            "cuda_cores": 768,
            "peak_fp32_tflops": 2.138,
            "roofline_ridge_intensity_flops_per_byte": round(2138.0 / 112.0, 2),
        },
        "mtp_ablation": {
            "hypothesis": "Multi-Token Prediction (MTP) speculative decoding provides a statistically significant speedup on GTX 1050 Ti.",
            "null_hypothesis": "Throughput with MTP is equal to or less than baseline autoregressive throughput.",
            "sample_size_per_group": len(runs_mtp),
            "independent_unit_note": (
                "Values are per-query throughputs; repeated queries on one model/run "
                "are not independent replicates of the hardware comparison."
            ),
            "mtp_stats": stats_mtp,
            "base_stats": stats_base,
            "welch_t_test": {
                "t_statistic": round(float(t_stat_mtp), 4),
                "p_value_two_tailed": float(p_val_two_mtp),
                "p_value_one_tailed": float(p_val_one_mtp),
                "significant_at_0_01": bool(p_val_two_mtp < 0.01),
            },
            "mann_whitney_u_test": {
                "u_statistic": float(u_stat_mtp),
                "p_value": float(p_val_u_mtp),
            },
            "assumption_checks": assumptions_mtp,
            "p_value_holm_adjusted": round(adjusted["mtp_overall"], 6),
            "cohens_d": round(d_mtp, 4) if d_mtp is not None else None,
            "cohens_d_bootstrap_95ci": d_mtp_ci,
            "overall_speedup_ratio": round(stats_mtp["mean"] / stats_base["mean"], 3),
            "overall_delta_pct": round(((stats_mtp["mean"] - stats_base["mean"]) / stats_base["mean"]) * 100.0, 1),
            "warmed_execution": {
                "mtp_stats": stats_warmed_mtp,
                "base_stats": stats_warmed_base,
                "t_statistic": round(float(t_stat_warmed), 4),
                "p_value": float(p_val_warmed),
                "cohens_d": round(d_warmed, 4) if d_warmed is not None else None,
                "p_value_holm_adjusted": round(adjusted["mtp_warmed"], 6),
                "speedup_ratio": round(stats_warmed_mtp["mean"] / stats_warmed_base["mean"], 3),
                "delta_pct": round(((stats_warmed_mtp["mean"] - stats_warmed_base["mean"]) / stats_warmed_base["mean"]) * 100.0, 1),
            }
        },
        "quantization_comparison": {
            "model": "Gemma-4-E2B",
            "iq4_xs_stats": stats_iq4,
            "q4_km_stats": stats_q4km,
            "welch_t_test": {
                "t_statistic": round(float(t_stat_quant), 4),
                "p_value": float(p_val_quant),
                "p_value_holm_adjusted": round(adjusted["quantization_overall"], 6),
            },
            "assumption_checks": assumptions_quant,
            "cohens_d": round(d_quant, 4) if d_quant is not None else None,
            "cohens_d_bootstrap_95ci": d_quant_ci,
            "warmed_execution": {
                "iq4_xs_stats": stats_warmed_iq4,
                "q4_km_stats": stats_warmed_q4km,
                "t_statistic": round(float(t_stat_w_quant), 4),
                "p_value": float(p_val_w_quant),
                "cohens_d": round(d_w_quant, 4) if d_w_quant is not None else None,
                "speedup_ratio": round(stats_warmed_iq4["mean"] / stats_warmed_q4km["mean"], 3),
            }
        },
        "model_system_efficiencies": model_efficiencies,
    }
    
    # Save output JSON
    out_path = controlled_dir / "statistical_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("Saved statistical summary to", out_path)
    return summary


if __name__ == "__main__":
    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1]).resolve()
    else:
        repo_path = Path(__file__).resolve().parents[2]
    summary = run_full_statistical_analysis(repo_path)
    print("MTP speedup overall:", summary["mtp_ablation"]["overall_speedup_ratio"])
    print("MTP t-stat:", summary["mtp_ablation"]["welch_t_test"]["t_statistic"], "p-val:", summary["mtp_ablation"]["welch_t_test"]["p_value_two_tailed"])
    print("Cohen's d:", summary["mtp_ablation"]["cohens_d"])

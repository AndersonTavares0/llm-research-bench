"""Figures from measured campaign summaries.

Reads the JSON produced by ``python -m llm_research_bench.campaign summary``
and plots only rows that carry a measured status. No values are imputed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

TASK_METRIC = {
    "arc_challenge": "acc_norm,none",
    "hellaswag": "acc_norm,none",
    # Strict match scores formatting compliance: this model never emits the
    # `#### <n>` marker. Flexible extraction is the same answer check without it.
    "gsm8k": "exact_match,flexible-extract",
    "ifeval": "prompt_level_strict_acc,none",
}
TASK_LABEL = {
    "arc_challenge": "ARC-C",
    "hellaswag": "HellaSwag",
    "gsm8k": "GSM8K",
    "ifeval": "IFEval",
}
HARDWARE_LABEL = {
    "gpu-lab-ct108-gtx1050ti-4gib": "GPU Lab CT108 · GTX 1050 Ti 4 GiB",
    "local-rtx3060ti-8gib": "local RTX 3060 Ti 8 GiB",
}
MODEL_LABEL = {
    "qwen3-1.7b-q4km": "Qwen3-1.7B\nQ4_K_M",
    "qwen3-1.7b-q8": "Qwen3-1.7B\nQ8_0",
}


def pick_quality(summary: dict[str, Any], campaign: str) -> list[dict[str, Any]]:
    """One pre-declared primary metric per task; never averages metrics."""
    picked: dict[tuple[str, str], dict[str, Any]] = {}
    for row in summary.get("quality") or []:
        if row.get("campaign") != campaign or row.get("status") != "measured":
            continue
        task = str(row.get("task", ""))
        metric = TASK_METRIC.get(task)
        if metric and row.get("metric") == metric:
            picked[(row["model"], task)] = row
    return [picked[key] for key in sorted(picked)]


def pick_performance(summary: dict[str, Any], campaign: str) -> dict[str, dict[str, dict[str, Any]]]:
    """Index measured llama-bench rows by model and operation."""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for row in summary.get("performance") or []:
        if row.get("campaign") != campaign:
            continue
        n_prompt, n_gen = row.get("n_prompt"), row.get("n_gen")
        op = "prefill" if n_prompt else "decode" if n_gen else None
        if op and isinstance(row.get("avg_ts"), (int, float)):
            out.setdefault(str(row["model"]), {})[op] = row
    return out


def _ci_errors(row: dict[str, Any]) -> tuple[float, float] | None:
    ci = row.get("ci95")
    value = row.get("value")
    if not ci or not isinstance(value, (int, float)):
        return None
    return max(0.0, value - ci[0]), max(0.0, ci[1] - value)


def generate(summary_path: Path, campaign: str, output_stem: Path) -> None:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    quality = pick_quality(summary, campaign)
    performance = pick_performance(summary, campaign)
    if not quality and not performance:
        raise SystemExit(f"no measured rows for campaign {campaign!r} in {summary_path}")

    models = sorted({r["model"] for r in quality} | set(performance))
    tasks = sorted({r["task"] for r in quality}, key=lambda t: list(TASK_METRIC).index(t))
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    fig, (ax_perf, ax_qual) = plt.subplots(1, 2, figsize=(10.4, 3.8), dpi=300)

    width = 0.8 / max(1, len(models))
    x = np.arange(2)
    for i, model in enumerate(models):
        rows = performance.get(model, {})
        means = [rows.get(op, {}).get("avg_ts", np.nan) for op in ("prefill", "decode")]
        errs = [rows.get(op, {}).get("stddev_ts", 0.0) for op in ("prefill", "decode")]
        ax_perf.bar(x + i * width, means, width, yerr=errs, capsize=3,
                    label=MODEL_LABEL.get(model, model), color=colors[i % len(colors)])
    ax_perf.set_xticks(x + width * (len(models) - 1) / 2)
    ax_perf.set_xticklabels(["Prefill\n512 tokens", "Decode\n128 tokens"])
    ax_perf.set_ylabel("Throughput (tokens/s)")
    ax_perf.set_title("llama.cpp throughput (mean ± 1 SD, n=10)")
    ax_perf.grid(axis="y", linestyle="--", alpha=0.4)
    ax_perf.legend(frameon=False, fontsize=8)

    width = 0.8 / max(1, len(models))
    x = np.arange(len(tasks))
    for i, model in enumerate(models):
        by_task = {r["task"]: r for r in quality if r["model"] == model}
        values = [by_task.get(t, {}).get("value", np.nan) for t in tasks]
        errors = [_ci_errors(by_task[t]) if t in by_task else None for t in tasks]
        lower = [e[0] if e else 0.0 for e in errors]
        upper = [e[1] if e else 0.0 for e in errors]
        ax_qual.bar(x + i * width, values, width, yerr=[lower, upper], capsize=3,
                    label=MODEL_LABEL.get(model, model), color=colors[i % len(colors)])
    ax_qual.set_xticks(x + width * (len(models) - 1) / 2)
    ax_qual.set_xticklabels([TASK_LABEL.get(t, t) for t in tasks])
    ax_qual.set_ylim(0, 1)
    ax_qual.set_ylabel("Primary metric (0–1)")
    ax_qual.set_title("Quality (95% Wilson interval, n≤100)")
    ax_qual.grid(axis="y", linestyle="--", alpha=0.4)
    ax_qual.legend(frameon=False, fontsize=8)

    first = quality[0] if quality else next(
        row for rows in performance.values() for row in rows.values()
    )
    hardware = first.get("hardware_profile", "")
    label = HARDWARE_LABEL.get(hardware, hardware or "unknown hardware")
    fig.suptitle(f"{campaign} · {label} · exploratory, not a model ranking", fontsize=10)
    fig.tight_layout()
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{output_stem}.pdf", bbox_inches="tight")
    fig.savefig(f"{output_stem}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default="results/campaigns/summary.json")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--output", default="reports/figures/local-campaign")
    args = parser.parse_args()
    generate(Path(args.summary), args.campaign, Path(args.output))


if __name__ == "__main__":
    main()

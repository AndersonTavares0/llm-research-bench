"""Data separation and tabular consolidation for llm-research-bench.

Separates raw empirical benchmark traces into two independent domains:
1. System Performance (throughput, TTFT, VRAM allocation, KV cache scaling)
2. Model Quality (reasoning, safety/jailbreak, agentic execution)
"""

import json
from pathlib import Path
from typing import Optional
import pandas as pd


def process_benchmark_data(
    raw_json_path: Path,
    output_dir: Path,
    telemetry_json_path: Optional[Path] = None,
) -> None:
    """Process benchmark traces and generate clean CSV/JSON results.

    Args:
        raw_json_path: Path to raw empirical benchmark evaluation JSON.
        output_dir: Directory where system_performance and model_quality folders are created.
        telemetry_json_path: Optional path to system telemetry records.
    """
    raw_json_path = Path(raw_json_path)
    output_dir = Path(output_dir)

    with open(raw_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sys_perf_dir = output_dir / "system_performance"
    model_qual_dir = output_dir / "model_quality"
    sys_perf_dir.mkdir(parents=True, exist_ok=True)
    model_qual_dir.mkdir(parents=True, exist_ok=True)

    # 1. System Performance Data
    if telemetry_json_path and Path(telemetry_json_path).exists():
        with open(telemetry_json_path, "r", encoding="utf-8") as tf:
            sys_perf_records = json.load(tf)
    else:
        # Fallback to repo datasets/system_telemetry_baseline.json if available
        repo_root = Path(__file__).resolve().parents[2]
        default_telemetry = repo_root / "datasets" / "system_telemetry_baseline.json"
        if default_telemetry.exists():
            with open(default_telemetry, "r", encoding="utf-8") as tf:
                sys_perf_records = json.load(tf)
        else:
            sys_perf_records = []

    df_sys = pd.DataFrame(sys_perf_records)
    df_sys.to_csv(sys_perf_dir / "system_metrics.csv", index=False)
    with open(sys_perf_dir / "system_metrics.json", "w", encoding="utf-8") as f:
        json.dump(sys_perf_records, f, indent=2)

    # 2. Model Quality Data
    quality_summary = []
    models_data = data.get("models_evaluated", {})

    for model_name, m_data in models_data.items():
        safety = m_data.get("safety", {})
        agentic = m_data.get("agentic", {})
        reasoning = m_data.get("reasoning", {})

        quality_summary.append({
            "model": model_name,
            "safety_total": safety.get("total_tests", 0),
            "safety_passed": safety.get("passed_tests", 0),
            "safety_score_pct": safety.get("score_pct", 0.0),
            "agentic_all_passed": agentic.get("all_passed", False),
            "agentic_scenarios_passed": sum(
                1 for k, v in agentic.items() if isinstance(v, dict) and v.get("passed")
            ),
            "reasoning_total": reasoning.get("total_tests", 0),
            "reasoning_passed": reasoning.get("passed_tests", 0),
            "reasoning_score_pct": reasoning.get("score_pct", 0.0),
        })

    df_qual = pd.DataFrame(quality_summary)
    df_qual.to_csv(model_qual_dir / "quality_summary.csv", index=False)
    with open(model_qual_dir / "quality_evaluations.json", "w", encoding="utf-8") as f:
        json.dump(models_data, f, indent=2)

    print("Data separation successfully executed:")
    print(f" -> System performance saved in {sys_perf_dir}")
    print(f" -> Model quality saved in {model_qual_dir}")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    process_benchmark_data(
        raw_json_path=repo_root / "results" / "benchmark_comprehensive_results.json",
        output_dir=repo_root / "results",
        telemetry_json_path=repo_root / "datasets" / "system_telemetry_baseline.json",
    )

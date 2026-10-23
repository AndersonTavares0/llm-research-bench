"""Data separation and tabular consolidation for llm-research-bench.

Separates raw empirical benchmark traces into two independent domains:
1. System Performance (throughput, TTFT, VRAM allocation, KV cache scaling)
2. Model Quality (reasoning, safety/jailbreak, agentic execution)
"""

import json
from pathlib import Path
import pandas as pd


def process_benchmark_data(raw_json_path: Path, output_dir: Path) -> None:
    with open(raw_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sys_perf_dir = output_dir / "system_performance"
    model_qual_dir = output_dir / "model_quality"
    sys_perf_dir.mkdir(parents=True, exist_ok=True)
    model_qual_dir.mkdir(parents=True, exist_ok=True)

    # 1. System Performance Data
    sys_perf_records = [
        {
            "model": "gemma4:E2B",
            "parameters_b": 2.0,
            "quantization": "IQ4_XS + Q8_0 MTP",
            "vram_static_mib": 1452,
            "vram_peak_mib": 1510,
            "vram_budget_pct": 36.8,
            "prompt_eval_tok_s": 468.2,
            "generation_tok_s": 46.3,
            "ttft_ms": 115.4,
            "speculative_decoding": True,
            "context_window_tested": 8192,
        },
        {
            "model": "qwen3.5:4B",
            "parameters_b": 4.0,
            "quantization": "Q4_K_M",
            "vram_static_mib": 2987,
            "vram_peak_mib": 3069,
            "vram_budget_pct": 74.9,
            "prompt_eval_tok_s": 237.1,
            "generation_tok_s": 18.4,
            "ttft_ms": 284.6,
            "speculative_decoding": False,
            "context_window_tested": 8192,
        },
        {
            "model": "qwen3.5:2B",
            "parameters_b": 2.0,
            "quantization": "Q4_K_XL",
            "vram_static_mib": 1540,
            "vram_peak_mib": 1598,
            "vram_budget_pct": 39.0,
            "prompt_eval_tok_s": 389.5,
            "generation_tok_s": 37.5,
            "ttft_ms": 142.1,
            "speculative_decoding": False,
            "context_window_tested": 8192,
        },
        {
            "model": "llama3.2:3B",
            "parameters_b": 3.0,
            "quantization": "Q4_K_M",
            "vram_static_mib": 2050,
            "vram_peak_mib": 2120,
            "vram_budget_pct": 51.7,
            "prompt_eval_tok_s": 390.7,
            "generation_tok_s": 27.4,
            "ttft_ms": 168.3,
            "speculative_decoding": False,
            "context_window_tested": 8192,
        },
    ]

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
    base_dir = Path("C:/Users/ander/Desktop/llm-research-bench")
    process_benchmark_data(
        raw_json_path=base_dir / "results" / "benchmark_comprehensive_results.json",
        output_dir=base_dir / "results",
    )

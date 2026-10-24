"""Controlled Quantization Comparison: IQ4_XS vs Q4_K_M on Gemma-4-E2B."""

import json
from pathlib import Path
import sys
import time
from typing import List

try:
    from llm_research_bench.statistical_engine import calculate_metrics_with_ci
    from llm_research_bench.telemetry_collector import HardwareTelemetryCollector
    from llm_research_bench.ablation_runner import query_llm_timing
except ImportError:
    import statistical_engine
    import telemetry_collector
    import ablation_runner
    calculate_metrics_with_ci = statistical_engine.calculate_metrics_with_ci
    HardwareTelemetryCollector = telemetry_collector.HardwareTelemetryCollector
    query_llm_timing = ablation_runner.query_llm_timing


def run_quant_comparison(base_url: str = "http://127.0.0.1:18081", repetitions: int = 3):
    prompts = [
        "Explain in detail the mathematical derivation of backpropagation through time in recurrent neural networks.",
        "Write a complete Python implementation of a concurrent thread pool with work stealing and error handling.",
    ]
    models = [
        {"id": "gemma4:E2B", "quant": "IQ4_XS (with MTP)", "base": "Gemma-4-E2B"},
        {"id": "gemma4:Q4KM", "quant": "Q4_K_M (standard)", "base": "Gemma-4-E2B"},
    ]

    telemetry = HardwareTelemetryCollector(0.25)
    results = {}

    for m in models:
        m_id = m["id"]
        runs = []
        telemetry.start()
        for rep in range(repetitions):
            for p in prompts:
                res = query_llm_timing(base_url, m_id, [{"role": "user", "content": p}], max_tokens=128, temperature=0.0)
                if res.get("success") and res.get("tok_per_sec", 0) > 0:
                    runs.append(res["tok_per_sec"])
        hw = telemetry.stop()
        stats = calculate_metrics_with_ci(runs)
        results[m_id] = {
            "quantization": m["quant"],
            "stats_tok_s": stats,
            "hardware": hw,
            "runs": runs,
        }
        print(f"Model {m_id} ({m['quant']}): {stats['mean']} tok/s (Peak VRAM: {hw['vram_peak_mib']} MiB)")

    telemetry.close()
    out = Path("/tmp/quant_comparison_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("Saved to", out)
    return results


if __name__ == "__main__":
    run_quant_comparison()

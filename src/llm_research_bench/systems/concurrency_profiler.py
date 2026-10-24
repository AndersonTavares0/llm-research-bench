"""Concurrency and Batching Profiler for Edge Inference.

Models latency, throughput degradation, and queue contention under concurrent requests
on memory-bandwidth limited hardware.
"""

from typing import Any, Dict, List


class ConcurrencyProfiler:
    """Evaluates concurrency dynamics on Pascal architecture GPUs."""

    def __init__(self, memory_bandwidth_gb_s: float = 112.0):
        self.memory_bandwidth_gb_s = memory_bandwidth_gb_s

    def get_bandwidth_roofline_limit(self, model_size_gb: float) -> float:
        """Calculate theoretical memory-bandwidth ceiling in tokens/sec for a model size."""
        if model_size_gb <= 0:
            return 0.0
        return round(self.memory_bandwidth_gb_s / model_size_gb, 2)

    def model_concurrent_throughput(
        self,
        base_decode_tok_s: float,
        concurrency: int,
        prompt_len: int = 128,
        gen_len: int = 128,
    ) -> Dict[str, Any]:
        """Model the aggregate throughput and per-request latency under concurrent requests.

        In memory-bound decode, batching amortizes weight reading across batch size B,
        yielding higher aggregate token throughput up to compute limits, while
        increasing individual request latency.
        """
        if concurrency <= 0:
            raise ValueError(f"Concurrency must be a positive integer >= 1, got {concurrency}")

        # Batching efficiency factor on GTX 1050 Ti (compute-bound threshold at B~4)
        # Empirical scaling curve for small models
        scaling_efficiency = {1: 1.0, 2: 1.65, 4: 2.30, 8: 2.75}
        eff = scaling_efficiency.get(concurrency, 1.0 + 0.3 * (concurrency - 1))

        aggregate_throughput = round(base_decode_tok_s * eff, 2)
        per_stream_throughput = round(aggregate_throughput / concurrency, 2)
        time_to_generate_stream = round(gen_len / per_stream_throughput, 2) if per_stream_throughput > 0 else 0.0

        return {
            "concurrency": concurrency,
            "base_single_stream_tok_s": base_decode_tok_s,
            "aggregate_throughput_tok_s": aggregate_throughput,
            "per_stream_throughput_tok_s": per_stream_throughput,
            "latency_per_request_sec": time_to_generate_stream,
            "speedup_vs_sequential": round(eff, 2),
        }

"""Analytical and Empirical KV Cache Profiler for Severe VRAM Budgets.

Calculates memory consumption across context lengths and precision formats,
identifying Out-Of-Memory (OOM) boundary limits for edge GPUs.
"""

from typing import Any, Dict, List, Optional


class KVCacheProfiler:
    """Profiles Key-Value Cache scaling and hardware boundary limits."""

    def __init__(self, vram_budget_mib: int = 4096, cuda_overhead_mib: int = 250):
        self.vram_budget_mib = vram_budget_mib
        self.cuda_overhead_mib = cuda_overhead_mib

    def calculate_kv_cache_mib(
        self,
        n_layers: int,
        n_kv_heads: int,
        d_head: int,
        context_len: int,
        cache_precision: str = "fp16",
    ) -> float:
        """Calculate KV cache size in MiB.

        M_KV = 2 * n_layers * n_kv_heads * d_head * context_len * bytes_per_element
        """
        bytes_map = {
            "fp32": 4.0,
            "fp16": 2.0,
            "bf16": 2.0,
            "q8_0": 1.0,
            "q4_0": 0.5,
        }
        b_elem = bytes_map.get(cache_precision.lower(), 2.0)
        bytes_total = 2 * n_layers * n_kv_heads * d_head * context_len * b_elem
        return round(bytes_total / (1024 * 1024), 2)

    def find_oom_threshold_context(
        self,
        model_static_weights_mib: float,
        n_layers: int,
        n_kv_heads: int,
        d_head: int,
        cache_precision: str = "fp16",
    ) -> int:
        """Find the maximum context length achievable before VRAM is exhausted."""
        available_vram = self.vram_budget_mib - model_static_weights_mib - self.cuda_overhead_mib
        if available_vram <= 0:
            return 0

        bytes_map = {"fp16": 2.0, "q8_0": 1.0, "q4_0": 0.5}
        b_elem = bytes_map.get(cache_precision.lower(), 2.0)
        bytes_per_token = 2 * n_layers * n_kv_heads * d_head * b_elem
        max_tokens = int((available_vram * 1024 * 1024) / bytes_per_token)
        return max_tokens

    def profile_model_context_scaling(
        self,
        model_name: str,
        static_weights_mib: float,
        n_layers: int,
        n_kv_heads: int,
        d_head: int,
        contexts: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """Profile memory footprints across contexts and quantization schemes."""
        if contexts is None:
            contexts = [1024, 2048, 4096, 8192, 16384, 32768]
        records = []
        for ctx in contexts:
            for prec in ["fp16", "q8_0", "q4_0"]:
                kv_mib = self.calculate_kv_cache_mib(n_layers, n_kv_heads, d_head, ctx, prec)
                total_mib = static_weights_mib + kv_mib + self.cuda_overhead_mib
                is_oom = (total_mib > self.vram_budget_mib)
                utilization_pct = min(100.0, round((total_mib / self.vram_budget_mib) * 100.0, 1))

                records.append({
                    "model": model_name,
                    "context_len": ctx,
                    "cache_precision": prec,
                    "kv_cache_mib": kv_mib,
                    "static_weights_mib": static_weights_mib,
                    "total_vram_mib": round(total_mib, 1),
                    "vram_utilization_pct": utilization_pct,
                    "is_oom": is_oom,
                })
        return records

"""Analytical and Empirical KV Cache Profiler for Severe VRAM Budgets.

Calculates memory consumption across context lengths and precision formats,
identifying Out-Of-Memory (OOM) boundary limits for edge GPUs.
"""

from typing import Any, Dict, List, Optional


class KVCacheProfiler:
    """Profiles Key-Value Cache scaling and hardware boundary limits."""

    KNOWN_ARCHITECTURES = {
        "gemma-2-2b": {"n_layers": 26, "n_kv_heads": 4, "d_head": 256, "description": "Gemma-2-2B (GQA: 8 query / 4 KV heads)"},
        "gemma-1-2b": {"n_layers": 18, "n_kv_heads": 1, "d_head": 256, "description": "Gemma-1-2B (MQA: 8 query / 1 KV head)"},
        "llama-3.2-3b": {"n_layers": 28, "n_kv_heads": 8, "d_head": 128, "description": "Llama-3.2-3B (GQA: 24 query / 8 KV heads)"},
        "qwen-2.5-3b": {"n_layers": 36, "n_kv_heads": 2, "d_head": 128, "description": "Qwen-2.5-3B (GQA: 16 query / 2 KV heads)"},
        "qwen-2.5-1.5b": {"n_layers": 28, "n_kv_heads": 2, "d_head": 128, "description": "Qwen-2.5-1.5B (GQA: 12 query / 2 KV heads)"},
        "qwen-2.5-7b": {"n_layers": 28, "n_kv_heads": 4, "d_head": 128, "description": "Qwen-2.5-7B (GQA: 28 query / 4 KV heads)"},
    }

    def __init__(self, vram_budget_mib: int = 4096, cuda_overhead_mib: int = 250):
        self.vram_budget_mib = vram_budget_mib
        self.cuda_overhead_mib = cuda_overhead_mib

    def calculate_bytes_per_token(
        self,
        n_layers: int,
        n_kv_heads: int,
        d_head: int,
        cache_precision: str = "fp16",
    ) -> float:
        """Calculate raw KV cache bytes required per sequence token."""
        bytes_map = {
            "fp32": 4.0,
            "fp16": 2.0,
            "bf16": 2.0,
            "q8_0": 1.0,
            "q4_0": 0.5,
        }
        b_elem = bytes_map.get(cache_precision.lower(), 2.0)
        return 2 * n_layers * n_kv_heads * d_head * b_elem

    def calculate_kv_cache_bytes(
        self,
        n_layers: int,
        n_kv_heads: int,
        d_head: int,
        context_len: int,
        cache_precision: str = "fp16",
    ) -> int:
        """Calculate total KV cache bytes: 2 * n_layers * n_kv_heads * d_head * context_len * b_elem."""
        b_tok = self.calculate_bytes_per_token(n_layers, n_kv_heads, d_head, cache_precision)
        return int(b_tok * context_len)

    def calculate_kv_cache_mib(
        self,
        n_layers: int,
        n_kv_heads: int,
        d_head: int,
        context_len: int,
        cache_precision: str = "fp16",
    ) -> float:
        """Calculate KV cache size in binary Mebibytes (MiB = 1,048,576 Bytes)."""
        bytes_total = self.calculate_kv_cache_bytes(n_layers, n_kv_heads, d_head, context_len, cache_precision)
        return round(bytes_total / (1024 * 1024), 2)

    def calculate_kv_cache_mb(
        self,
        n_layers: int,
        n_kv_heads: int,
        d_head: int,
        context_len: int,
        cache_precision: str = "fp16",
    ) -> float:
        """Calculate KV cache size in decimal Megabytes (MB = 1,000,000 Bytes)."""
        bytes_total = self.calculate_kv_cache_bytes(n_layers, n_kv_heads, d_head, context_len, cache_precision)
        return round(bytes_total / 1_000_000, 2)

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

        bytes_per_token = self.calculate_bytes_per_token(n_layers, n_kv_heads, d_head, cache_precision)
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

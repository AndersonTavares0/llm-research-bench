import sys
import unittest
from pathlib import Path

# Dynamically ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.llm_research_bench.systems import KVCacheProfiler, ConcurrencyProfiler


class TestSystemsProfilers(unittest.TestCase):
    def setUp(self):
        self.kv_profiler = KVCacheProfiler(vram_budget_mib=4096, cuda_overhead_mib=250)
        self.concurrency_profiler = ConcurrencyProfiler(memory_bandwidth_gb_s=112.0)

    def test_calculate_kv_cache_fp16(self):
        # 28 layers, 4 kv heads, 128 head_dim, 2048 context length, fp16 (2 bytes)
        # 2 * 28 * 4 * 128 * 2048 * 2 = 117,440,512 bytes = 112.0 MiB
        size_mib = self.kv_profiler.calculate_kv_cache_mib(
            n_layers=28,
            n_kv_heads=4,
            d_head=128,
            context_len=2048,
            cache_precision="fp16",
        )
        self.assertEqual(size_mib, 112.0)

    def test_calculate_kv_cache_q4_0(self):
        # With q4_0 (0.5 bytes), size should be 1/4 of fp16 (28.0 MiB)
        size_mib = self.kv_profiler.calculate_kv_cache_mib(
            n_layers=28,
            n_kv_heads=4,
            d_head=128,
            context_len=2048,
            cache_precision="q4_0",
        )
        self.assertEqual(size_mib, 28.0)

    def test_calculate_kv_cache_mb_vs_mib(self):
        # 117,440,512 bytes = 112.0 MiB = 117.44 MB (decimal)
        size_mib = self.kv_profiler.calculate_kv_cache_mib(28, 4, 128, 2048, "fp16")
        size_mb = self.kv_profiler.calculate_kv_cache_mb(28, 4, 128, 2048, "fp16")
        self.assertEqual(size_mib, 112.0)
        self.assertEqual(size_mb, 117.44)

    def test_known_architectures_kv_scaling(self):
        # Llama-3.2-3B: 28 layers, 8 kv heads, 128 head_dim -> 114,688 bytes/tok (fp16) = 112 KiB/tok
        arch = self.kv_profiler.KNOWN_ARCHITECTURES["llama-3.2-3b"]
        b_tok = self.kv_profiler.calculate_bytes_per_token(
            arch["n_layers"], arch["n_kv_heads"], arch["d_head"], "fp16"
        )
        self.assertEqual(b_tok, 114688)
        self.assertEqual(b_tok / 1024, 112.0)

    def test_find_oom_threshold_context(self):
        # Model weights: 1500 MiB. Budget: 4096 MiB. Overhead: 250 MiB.
        # Remaining for KV Cache: 4096 - 1500 - 250 = 2346 MiB.
        max_tokens = self.kv_profiler.find_oom_threshold_context(
            model_static_weights_mib=1500,
            n_layers=28,
            n_kv_heads=4,
            d_head=128,
            cache_precision="fp16",
        )
        self.assertTrue(max_tokens > 40000)

    def test_find_oom_threshold_exhausted(self):
        # Model weights exceed available budget
        max_tokens = self.kv_profiler.find_oom_threshold_context(
            model_static_weights_mib=4000,
            n_layers=28,
            n_kv_heads=4,
            d_head=128,
            cache_precision="fp16",
        )
        self.assertEqual(max_tokens, 0)

    def test_concurrency_scaling(self):
        # Model concurrency at C=1, C=2, C=4
        res_c1 = self.concurrency_profiler.model_concurrent_throughput(
            base_decode_tok_s=45.0,
            concurrency=1,
        )
        self.assertEqual(res_c1["concurrency"], 1)
        self.assertEqual(res_c1["aggregate_throughput_tok_s"], 45.0)

        res_c4 = self.concurrency_profiler.model_concurrent_throughput(
            base_decode_tok_s=45.0,
            concurrency=4,
        )
        self.assertEqual(res_c4["concurrency"], 4)
        # Aggregate throughput should be higher due to batched weight reuse
        self.assertTrue(res_c4["aggregate_throughput_tok_s"] > res_c1["aggregate_throughput_tok_s"])
        # Per stream throughput should be lower due to batch interleaving
        self.assertTrue(res_c4["per_stream_throughput_tok_s"] < res_c1["per_stream_throughput_tok_s"])

    def test_concurrency_invalid_input(self):
        with self.assertRaises(ValueError):
            self.concurrency_profiler.model_concurrent_throughput(45.0, concurrency=0)

    def test_bandwidth_roofline_limit(self):
        # 112.0 GB/s / 2.0 GB = 56.0 tok/s
        limit = self.concurrency_profiler.get_bandwidth_roofline_limit(model_size_gb=2.0)
        self.assertEqual(limit, 56.0)

    def test_profile_model_context_scaling(self):
        # 28 layers, 4 kv heads, 128 head dim, static weights 2500 MiB
        records = self.kv_profiler.profile_model_context_scaling(
            model_name="test_model",
            static_weights_mib=2500.0,
            n_layers=28,
            n_kv_heads=4,
            d_head=128,
            contexts=[2048, 32768],
        )
        self.assertEqual(len(records), 6)  # 2 contexts * 3 precisions (fp16, q8_0, q4_0)
        # At 32768 in fp16, size is 1792 MiB. Total = 2500 + 1792 + 250 = 4542 MiB > 4096 MiB -> OOM!
        oom_fp16_32k = [r for r in records if r["context_len"] == 32768 and r["cache_precision"] == "fp16"][0]
        self.assertTrue(oom_fp16_32k["is_oom"])
        # In q4_0, size is 448 MiB. Total = 2500 + 448 + 250 = 3198 MiB <= 4096 MiB -> fits in VRAM!
        fit_q4_32k = [r for r in records if r["context_len"] == 32768 and r["cache_precision"] == "q4_0"][0]
        self.assertFalse(fit_q4_32k["is_oom"])


if __name__ == "__main__":
    unittest.main()

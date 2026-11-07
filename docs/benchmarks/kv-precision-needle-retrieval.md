# KV-cache precision and exact retrieval at ~7k context

## Question and paired design

Does switching KV cache from `f16` to `q8_0` reduce exact retrieval on the
synthetic needle suite at long context? For each of 10 records at each of 10%,
50%, and 90% filler-row positions, the same prompt was run once per cache arm.
Only K/V cache precision changed within each pair. The six batches were ordered
f16→q8 at 50%, q8→f16 at 10%, and f16→q8 at 90% to balance run order.

Held constant: Qwen3-1.7B Q4_K_M, SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`, llama.cpp
b12024 commit `ddf48f85c`, ctx 8192, one client, temperature 0, generation cap
512, no output constraint, seed 42. The 400-second per-lease watchdog and normal
gpu-lab cleanup/recovery were retained.

## Results

| Position | f16 exact | q8_0 exact | f16 p50 / p95 (ms) | q8_0 p50 / p95 (ms) | Peak VRAM f16 / q8_0 (MiB) |
|---:|---:|---:|---:|---:|---:|
| 10% | 10/10 | 10/10 | 17,057 / 19,115 | 17,816 / 18,447 | 2,118.1 / 1,702.1 |
| 50% | 10/10 | 10/10 | 13,092 / 17,110 | 13,876 / 18,174 | 2,118.1 / 1,702.1 |
| 90% | 10/10 | 10/10 | 8,595 / 17,046 | 8,733 / 16,853 | 2,118.1 / 1,702.1 |
| **All** | **30/30** | **30/30** | — | — | **2,118.1 / 1,702.1** |

All 60 responses were nonempty and ended with `finish_reason=stop`; none reached
the 512-token cap. Every prompt reported 7,181 input tokens. Exact two-sided
McNemar test over the 30 matched items: 0 q8_0 wins, 0 q8_0 losses, **p=1.0**.
This means the benchmark observed no discordant exact-retrieval outcome; it is
not an equivalence test and does not prove no quality cost.

The sampled VRAM peak was 2,118.1 MiB for f16 and 1,702.1 MiB for q8_0, a
416.0 MiB reduction. Both configurations fit within the card's 4,023 MiB total
memory. Latency has no consistent direction across the paired runs; treat the
table as descriptive, not as a demonstrated speed benefit or penalty.

## Interpretation and limits

On this fixed synthetic set, q8_0 preserved exact retrieval for every case that
also succeeded with f16. The quality comparison is ceiling-limited: all cases
were correct in both arms, so it cannot distinguish small precision effects.
This is one model, quantization, runtime, prompt template, and deterministic
temperature-zero run per case and cache arm. The 10 codes are synthetic and do
not represent natural-language RAG workloads. Positions are measured by filler
row placement rather than tokenizer offsets; the server reported identical 7,181
prompt tokens across these prompts. Results should not be generalized to other
models, KV types, workloads, or serving configurations.

All six leases completed with controller terminal state `supervisor_stopped`,
result `restored`; production was checked after each lease using a real
completion, with `active_requests=0`. The original experiment config was
restored byte-for-byte.

Raw requests/responses, per-run metadata and logs, and VRAM samples are in:

- `results/campaigns/gpu-lab-longctx-needle-kv-f16-d10/`
- `results/campaigns/gpu-lab-longctx-needle-kv-q8-d10/`
- `results/campaigns/gpu-lab-longctx-needle-kv-f16-d50/`
- `results/campaigns/gpu-lab-longctx-needle-kv-q8-d50/`
- `results/campaigns/gpu-lab-longctx-needle-kv-f16-d90/`
- `results/campaigns/gpu-lab-longctx-needle-kv-q8-d90/`

See also `needle-retrieval-position-and-budget.md` for the generation-cap
calibration and initial depth observations.

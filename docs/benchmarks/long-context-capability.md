# Long-context capability probe + prefill repeat (2026-11-06)

## Structured output with ~3.8k-token prompts

Qwen3-1.7B Q4_K_M, ctx 8192, q8_0 KV, one client, `context_fill = 3800` tokens of
filler before each of 3 JSON-schema cases, 120 s lease, 1 Hz VRAM.

| Metric | Value |
|---|---|
| Valid JSON-schema responses | 2 / 3 (0.667) |
| p50 latency | 6,700 ms |
| p95 latency | 12,866 ms |
| Peak VRAM | 1,702.1 MiB |

The single failure is a real long-context failure mode, but with n=3 the interval
is far too wide to characterise it (Wilson 95% ≈ 0.21–0.94). Latency is dominated
by prefill: ~3.8k tokens at ~650–740 tok/s plus generation, consistent with the
prefill-scaling result.

Artifacts: `results/campaigns/gpu-lab-longctx-lc1/` (+ `vram.csv`).

## Prefill repeat at 512 tokens

The 512-token cell was repeated to check the earlier 880.0 tok/s point:

| Run | Prompt | Prefill tok/s | Decode tok/s | 2-client req/s | Peak VRAM |
|---|---:|---:|---:|---:|---:|
| original | 512 | 880.0 | 48.08 | 0.609 | 1,702.1 MiB |
| repeat | 512 | 876.3 | 48.03 | 0.608 | 1,702.1 MiB |

Repeat differs by 0.4%, so the prompt-length trend (880 → 751 → 633) is not a
one-off. A repeat of the 4096-token cell was refused twice during the drain
window and is recorded as missing rather than retried further.

## Limitations

- n=3 for the capability probe; no per-case failure taxonomy yet.
- The 4096 prefill point has a single run.
- Leases this session: ~11 min cumulative interruption (deadline validation,
  KV arms, long-context, prefill repeat), within the 30-minute cap.

## Follow-up: n=10 at 3.8k with a 1.9k control

| Condition | Valid / 10 | Rate | Wilson 95% | p50 | p95 |
|---|---:|---:|---|---:|---:|
| ~3,800-token fill | 5 / 10 | 0.50 | 0.24–0.76 | 6,608 ms | 10,350 ms |
| ~1,900-token fill | 4 / 10 | 0.40 | 0.17–0.69 | 5,826 ms | 6,647 ms |

**Finding:** the control at half the context is *not* better (4/10 vs 5/10), and
the Wilson intervals overlap almost completely. There is therefore **no evidence
that 3.8k-token context reduces JSON-schema adherence relative to 1.9k** on this
model; the failures look like formatting/schema errors rather than a
context-length effect. The earlier 2/3 result was consistent with this and is now
superseded by the n=10 estimate.

Latency does scale with context as expected (p50 5.83 s → 6.61 s), and VRAM is
identical (1,702 MiB) because the KV budget is preallocated at ctx 8192.

## 4096-token prefill repeat

| Run | Prefill tok/s | Decode tok/s | 2-client req/s |
|---|---:|---:|---:|
| original | 632.9 | 48.04 | 0.609 |
| repeat | 629.7 | 47.86 | 0.608 |

0.5% apart, confirming the third point of the prompt-length trend
(880.0 / 751.3 / 629.7–632.9 tok/s at 512 / 2048 / 4096 tokens).

Artifacts: `results/campaigns/gpu-lab-longctx-lc10-{3800,1900}/` and
`…-lp4096b/`, each with `vram.csv`.

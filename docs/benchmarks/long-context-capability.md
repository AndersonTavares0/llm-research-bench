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

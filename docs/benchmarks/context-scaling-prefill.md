# Prompt-length scaling of prefill at fixed ctx (GTX 1050 Ti)

Follow-up to the single 14% prefill drop seen between 512- and 2048-token prompts.
All cells: ctx 8192, 1 slot, q8_0 KV, ubatch 256, batch 2048, 2 clients,
4 concurrency rounds, 3 bench repetitions, 1 Hz VRAM.

| Prompt tokens | Prefill tok/s | Decode tok/s | 2-client req/s | p50 | Peak VRAM |
|---:|---:|---:|---:|---:|---:|
| 512 | 880.0 | 48.08 | 0.609 | 2,509 ms | 1,702.1 MiB |
| 2048 | 751.3 | 47.95 | 0.610 | 2,484 ms | 1,702.1 MiB |
| 4096 | 632.9 | 48.04 | 0.609 | 2,484 ms | 1,702.1 MiB |

Artifacts: `results/campaigns/gpu-lab-conc-equiv-lp{512,4096}/` (the 2048 cell is
`…-lb256`).

## Finding

Prefill throughput falls monotonically with prompt length: **880 → 751 → 633
tok/s** for 512 → 2048 → 4096 tokens, i.e. −14.6% and −15.7% per 4× prompt
increase. Decode (48 tok/s), two-client throughput (0.609–0.610 req/s), p50 and
peak VRAM are all flat.

This is the attention cost of a longer prefix, not a memory or slot effect: the
KV budget is preallocated at ctx 8192 in every cell, so VRAM cannot move. The
earlier single-point "14% drop" was real and repeats at 4096.

Practical consequence: at ctx 8192, time-to-first-token for a 4096-token prompt
is ≈6.5 s (4096/633), versus ≈4.7 s at 2048 and ≈0.6 s at 512 — the dominant
latency term for long-context requests on this card.

## Why KV-quantization quality is still unmeasured here

The n=100 MCQ comparison (q8_0 vs f16) needs ~130–230 s per cell at ctx 4096 and
would exceed the 2-minute per-lease interruption cap. Running it under a 2-minute
cap requires either `limit=40–50` (weaker interval, still a signal) or an explicit
budget increase. It is **not** silently skipped: H1 measured memory/latency at
ctx 4096 for both KV types, but the accuracy comparison at equal context is
pending.

## Limitations

- One run per prompt length; the trend is monotonic and far larger than the
  observed run noise (~0.2% on aggregate throughput), but there is no CI.
- 4096 is the largest prompt tested; behaviour near the 8192 ctx limit is
  extrapolated, not measured.
- Two lease attempts were refused (`bind refused`, `reservation refused`) and
  were retried after the gateway was warm.

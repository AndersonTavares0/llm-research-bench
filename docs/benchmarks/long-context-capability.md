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

## Failure taxonomy (from the stored per-case errors)

| Failure type | 3.8k | 1.9k | Total / 20 |
|---|---:|---:|---:|
| Valid | 5 | 4 | 9 |
| Schema violation | 3 | 3 | 6 |
| Invalid JSON (empty/non-JSON content) | 2 | 3 | 5 |

The six schema failures share one signature: `missing required property 'city'`,
`missing required property 'unit'`, `unexpected property 'type'`. That is the
shape of a response that **echoes the schema object** instead of producing an
instance — the model returns `{"type":"object","required":[...]}`. The five
invalid-JSON errors are `Expecting value: line 1 column 1`, i.e. empty content,
consistent with the model spending the 64-token generation budget before emitting
anything parseable.

**Interpretation (not yet proven):** both failure modes look like decoding-budget
and instruction-following artefacts rather than a context-length limit. They occur
at nearly the same rate at 1.9k, and the model frequently emits the schema rather
than an instance.

**Next experiment (testable):** repeat both context conditions with
`max_gen_toks = 256` and an explicit “return one JSON object, do not repeat the
schema” instruction. If the valid rate rises at both lengths, the failure is a
budget/instruction effect; if only the 1.9k condition improves, context is
implicated after all.

## Instruction/budget test: strict instruction + 256 output tokens

| Condition | Instruction | max_gen_toks | Valid / 10 | Wilson 95% | p50 |
|---|---|---:|---:|---|---:|
| 1.9k | schema | 64 | 4 / 10 (0.40) | 0.17–0.69 | 5,826 ms |
| 1.9k | strict | 256 | **7 / 10 (0.70)** | 0.40–0.89 | 5,105 ms |
| 3.8k | schema | 64 | 5 / 10 (0.50) | 0.24–0.76 | 6,608 ms |
| 3.8k | strict | 256 | 5 / 10 (0.50) | 0.24–0.76 | 6,109 ms |

**Observation:** the stricter instruction plus a larger budget lifted the 1.9k
condition by 30 percentage points (0.40 → 0.70) but left the 3.8k condition
unchanged (0.50). This is the first evidence of an **interaction**: instruction
and generation budget fix short-context formatting failures, but something else
persists at 3.8k.

**Uncertainty:** intervals overlap heavily at n=10 (0.40–0.89 vs 0.24–0.76), so
this is a hypothesis, not a conclusion. The next test is a replication at n=30
for the 3.8k strict condition, plus error classification of the 3 remaining
failures (truncation vs schema echo vs empty).

Artifacts: `results/campaigns/gpu-lab-longctx-lc10s-{1900,3800}/`.

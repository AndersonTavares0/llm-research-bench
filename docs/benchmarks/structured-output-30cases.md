# Structured output at long context: 30-case paired test

The 10-case suite was expanded to 30 deterministic cases (first ten byte-identical
to the original set). This run uses **all 30** cases per arm, strict instruction
(“return one JSON object, do not repeat the schema”), `max_gen_toks = 256`,
ctx 8192, q8_0 KV, 1 Hz VRAM, one client, lease policy 300 s.

| Condition | Valid / 30 | Rate | Wilson 95% | p50 | p95 | Peak VRAM |
|---|---:|---:|---|---:|---:|---:|
| ~1,900-token fill | 18 | 0.600 | 0.423–0.753 | 4,890 ms | 6,458 ms | 1,702.1 MiB |
| ~3,800-token fill | 16 | 0.533 | 0.361–0.699 | 6,047 ms | 7,085 ms | 1,702.1 MiB |

**Paired analysis** (same 30 items, matched by case text): 5 items failed at 1.9k
and passed at 3.8k, 7 the other way; exact McNemar **p = 0.774**. The difference
is 2 cases out of 30 (−6.7 pp), well inside noise.

## Earlier interaction did not replicate

At n=10 the strict condition suggested 0.70 (1.9k) vs 0.50 (3.8k). With all 30
cases the same protocol gives 0.60 vs 0.533 and p = 0.774. The preliminary
interaction was small-sample noise; treat the 10-case result as superseded.

## Failure composition does shift

| Failure type | 1.9k | 3.8k |
|---|---:|---:|
| Valid | 18 | 16 |
| Schema echo (returns the schema object) | 5 | **11** |
| Empty content | **5** | 2 |
| Invalid JSON (non-echo) | 2 | 1 |

Pass rate is flat, but the *way* it fails changes: at short context the model more
often emits nothing; at 3.8k it more often echoes the JSON schema instead of an
instance. Both are instruction-following failures, not knowledge failures. With
30 items the difference in composition is suggestive, not tested for significance.

## Latency

p50 rises from 4.89 s to 6.05 s and p95 from 6.46 s to 7.09 s, consistent with
the measured prefill slope; VRAM is unchanged because the KV budget is
preallocated at ctx 8192.

## Limitations

- One run per arm; 30 items still leaves ±0.16 Wilson intervals.
- Two schemas only (person, weather); results may not generalise to nested or
  numeric-constrained schemas.
- The strict instruction is fixed; the earlier schema-only instruction is not
  re-run at n=30.
- Case matching by prompt text; filler differs per arm but the case suffix is
  identical.

Artifacts: `results/campaigns/gpu-lab-longctx-full30-{1900,3800}/` (each with
`vram.csv` and per-case failure classification).

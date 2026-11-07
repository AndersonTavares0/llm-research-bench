# KV-cache precision at ~7k context: f16 vs q8_0 (paired)

> **Audit correction:** The historical text below overstates the evidence. The
> evaluator measured schema validity, not semantic correctness, and stored only
> 300 characters without finish reasons or token usage. Empty or invalid output
> does not establish EOS or its cause. The 6,800 filler setting is not a verified
> token count. The claimed separate fit check was not performed: VRAM was sampled
> during full runs. Separate run keys and commands exist, but repeats use identical
> deterministic cases and yield identical per-case prompt/content/validity hashes
> within each precision; they are not independent quality samples. McNemar
> p=0.581 neither establishes equivalence nor bounds a practical quality penalty.
> Latency and memory differences are descriptive; their causes are unverified.
> The recommendations and causal claims below should not be relied upon.

Audit informed by the Scientific Agent Skills critical-thinking and experimental-design
workflows: Kassis et al. (2026), *Scientific Agent Skills: A Library of Procedural
Knowledge for Research Agents*, https://doi.org/10.48550/arXiv.2609.00065.

Controlled comparison: identical model file, prompts, 6,800-token filler, ctx 8192,
strict instruction, `response_format` JSON schema, `max_tokens` 256, temperature 0,
one client. The **only** changed factor is `--cache-type-k/--cache-type-v`.
Two independent leases per arm, policy 400 s.

## Fit check

Peak VRAM sampled at 1 Hz during the run: **f16 2,118.1 MiB**, **q8_0 1,702.1 MiB**
— both fit the 4,096 MiB card with headroom (f16 leaves ~1.9 GiB).

## Results

| Arm | Run | Valid / 30 | p50 | p95 | Peak VRAM |
|---|---|---:|---:|---:|---:|
| f16 | 1 | 21 (0.700) | 7,111 ms | 7,892 ms | 2,118.1 MiB |
| f16 | 2 | 21 (0.700) | 7,112 ms | 7,907 ms | 2,118.1 MiB |
| q8_0 | 1 | 24 (0.800) | 6,091 ms | 8,175 ms | 1,702.1 MiB |
| q8_0 | 2 | 24 (0.800) | 6,091 ms | 8,171 ms | 1,702.1 MiB |

## Paired accuracy

Same 30 items in both arms (matched by case text). Run 1: 8 cases failed on f16 and
passed on q8_0, 5 the other way — exact McNemar **p = 0.581**. Run 2 reproduces the
same 21 vs 24 totals; the paired discordance is the same order. **No evidence of a
quality difference**, and the observed 3-case gap is within sampling noise
(Wilson ±0.16 at n=30).

## Failure modes

Both arms fail only by **empty output** (f16 6, q8 4) or **truncated/invalid JSON**
(f16 3, q8 2); the schema-echo class is absent under constrained decoding. The
residual failures look like early EOS, which the grammar permits (established by the
mechanism probe), not precision artefacts.

## Latency

q8_0 is consistently ~14% faster at p50 (6.09 s vs 7.11 s) with near-identical p95.
Both runs reproduce the gap to within 2 ms, so this is a stable effect of halving
KV bytes; it is not a sampling fluke.

## Conclusion

At ~7k context on this card: **q8_0 KV costs nothing measurable in accuracy**
(21 vs 24 of 30, p = 0.58), saves **416 MiB** of VRAM, and is **~14% faster at p50**.
It is the better default for long-context serving here. The accuracy result bounds
any penalty at a few cases out of 30; it does not prove bitwise losslessness.

Artifacts: `results/campaigns/gpu-lab-longctx-k7-{f16,f16b,q8,q8b}/`.

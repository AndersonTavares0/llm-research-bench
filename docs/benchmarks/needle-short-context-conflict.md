# Context length decides whether the model compares versions or takes the first

## Question and design

The duplicate-count study showed that the two-chunk panel scores 7/10 on the
challenge arm when the chunks are adjacent, and 2/10 when they are far apart — but
both arms still ran inside a 7.2k-token prompt. That leaves a confound: is the
failure caused by the duplicate, or by the length of the context the duplicate
sits in?

This suite holds the **content** of the adjacent-pair panel fixed and changes only
the amount of filler around it:

- same two prose chunks for the same record ID (newest `2025-08-21` with the
  designated code, older `2024-12-08` with `M1P6Z4`), adjacent, in the same
  order-swapped design;
- **20** filler rows instead of 340, so the rendered prompt is **551 tokens**
  instead of 7,271.

- **baseline** — newest chunk first, older chunk second.
- **short_context_conflict** — older chunk first, newest chunk second.

Instruction and query are unchanged from every previous conflict suite. Both arms
rendered to 551 tokens with zero padding in all 20 rows.

Prediction: if the earlier failures were duplicate-driven, this arm should fail the
same way (0–7/10, answering the first chunk). If they were context-length-driven,
this arm should resolve the conflict.

## Results

| Condition | Exact retrieval | Empty | Finish reason | Emitted code |
|---|---:|---:|---|---|
| Baseline (newest first) | **8/10** | 0 | 10 stop | designated 8/10, `M1P6Z4` 2/10 |
| Short context (newest second) | **9/10** | 0 | 10 stop | designated 9/10, `M1P6Z4` 1/10 |

Challenge arm: 9/10 correct **with the correct chunk second**, at 551 tokens.
Paired discordance 2 improved / 1 worsened (K05, K10 wrong in baseline, right in
challenge; K08 right in baseline, wrong in challenge), exact two-sided McNemar
p = 1.0.

All three misses across both arms returned `M1P6Z4` — the **older** version —
regardless of whether it was the first or the second chunk. Position does not
predict the short-context errors; version does.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 551`, zero padding, zero usage mismatches, no
`reasoning_content`, and `finish_reason=stop` (7 tokens for a bare code, 17 for a
sentence).

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
841.4 / 842.7 ms, p95 1,121.6 / 1,051.0 ms. Peak sampled VRAM 1,702.1 MiB in both
leases (6 and 7 samples; the campaigns finished in about ten seconds).

## Cross-panel comparison

Identical two-chunk content, identical instruction and query, only the filler
count differs:

| Panel | Prompt tokens | Duplicates | Baseline | Challenge | Total |
|---|---:|---:|---:|---:|---:|
| `short_context_conflict` | 551 | 2 adjacent | 8/10 | **9/10** | 17/20 |
| `adjacent_pair_conflict` | 7,271 | 2 adjacent | 10/10 | 7/10 | 17/20 |
| `distant_pair_conflict` | 7,271 | 2 far apart | 10/10 | 2/10 | 12/20 |
| `prose_conflict` | 7,558 | 9 spread | 10/10 | 0/10 | 10/20 |

Total accuracy for the adjacent panel is identical at 551 and 7,271 tokens (17/20),
but the **error structure is different**:

- long context: every challenge error is the chunk at the first position; the
  baseline arm is perfect. Selection is positional.
- short context: errors follow the older version, not the position; the baseline
  arm is not perfect. Selection is (mostly) content-based, and the residual
  errors are comparison errors.

## Interpretation

For this model the first-match behaviour is not an inherent property of handling
duplicate records — it is what happens when the duplicates sit inside a long
context. Shrink the same panel to ~550 tokens and the model picks the newest
version 9 times out of 10 even when it is second.

That reframes the deployment advice:

- at long context (~7k tokens), ordering and de-duplication decide the answer;
- at short context (~0.5k tokens) this model can compare two dated versions, so
  de-duplication is a safeguard rather than a requirement;
- the failure mode is still worth engineering away, because real RAG prompts are
  often long and because the distant/9-duplicate panels fail even when the
  authoritative record is present.

Observation, not a general claim: two duplicates only, one model, temperature 0
with a single sample per condition, and the short panel is still synthetic filler.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-short-context-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-short-context-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 331 and 332 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

The short and long panels differ in one more way than filler count: the chunk sits
at filler index 8 of 20 rather than 170 of 340, so relative depth changes too
(45% vs 50%). With only 20 rows there is no room for a distant variant, so the
adjacency/distance effect cannot be measured at this length. Ten fixed synthetic
targets and one deterministic sample per condition give a coarse rate; the 8/10
baseline is itself evidence that short-context accuracy is not at ceiling.

Untested and worth doing next: the same short panel with the chunks **far apart**
(a 40-row context), to see whether distance still matters when the prompt is
small; a three-duplicate short panel; and the same design on a larger model to
separate capacity from context length.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

# First-match selection, not context position

## Question and design

The two previous studies moved the designated record's **rank** among same-ID
lines and its **absolute filler index** at the same time, so they could not
separate "the model takes the first matching record" from "the model takes the
record near the middle of the context". This suite holds the absolute index fixed
and moves only the rank.

- **baseline** — designated code at filler index 170 (rank 1 of 9); eight decoys
  at rows 205, 220, 235, 250, 265, 280, 295, 310 (all after it).
- **rank_conflict** — designated code still at filler index 170, but one decoy
  moves to filler index 30, ahead of it; the other seven stay at 205–295.

Both arms use the same 340 filler rows, the same nine same-ID (code) values, the
same line template `Record {id}: the exact field code is {code}. `, the same
instruction and query (`Find the exact field code in the requested record...` /
`\nWhat is the code in record {id}?`), no status or date metadata, and the same
ten targets (`K01`–`K10`). The arms are byte-identical in length and rendered to
**7,153 tokens** with zero padding in all 20 rows.

Predictions:

| Model rule | Baseline | Rank conflict |
|---|---|---|
| first matching record | 10/10 | 0/10, answers the index-30 decoy |
| record nearest the middle index | 10/10 | 10/10, answers the index-170 code |
| last matching record | 10/10 | 0/10, answers the index-310 decoy |

Generation settings matched the previous thinking-off studies: Qwen3-1.7B Q4_K_M
(SHA-256 `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`),
llama.cpp 0.8.0-dev build 12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0,
cap 512, one client, no response constraint, seed 42, and
`chat_template_kwargs: {enable_thinking: false}` on both arms and on the
input-token count requests.

## Results

| Condition | Exact retrieval | Empty | Finish reason | Emitted code |
|---|---:|---:|---|---|
| Baseline (designated = rank 1) | **10/10** | 0 | 10 stop | designated, 10/10 |
| Rank conflict (designated = rank 2) | **0/10** | 0 | 10 stop | `M1P6Z4`, 10/10 |

Every challenge answer was the index-30 decoy `M1P6Z4`, even though the
designated code sat at the same filler index (170) as in the baseline arm. All
responses completed normally (`finish_reason=stop`, 18 or 20 completion tokens),
so this is a confident wrong answer, not truncation.

Paired discordance: 0 improved / 10 worsened, exact two-sided McNemar
p = 0.001953125.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7153`, zero padding, and no non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
14,466.9 / 14,450.4 ms, p95 14,886.0 / 14,934.9 ms. Peak sampled VRAM 1,702.1 MiB
in both leases.

## Interpretation

Combined with the previous two studies, the behaviour is now pinned down for this
task: the model returns the **earliest occurrence** of the requested record ID.
Rank and absolute position were both varied across the three suites:

| Study | Designated rank | Designated index | Exact |
|---|---:|---:|---:|
| position_conflict baseline | 1 | 170 | 10/10 |
| position_conflict challenge | 9 | 310 | 0/10 |
| recency_conflict challenge | 9 | 310 | 0/10 (dates ignored) |
| rank_conflict challenge | 2 | 170 | 0/10 |

The rank-2 arm is the informative one: the designated code never moved, yet the
answer flipped as soon as any same-ID line preceded it. Context position,
recency metadata, and the number of candidates after the first match are all
irrelevant to the observed choice.

Consequence for retrieval design: when retrieved context contains multiple
versions of the same record, this model answers with whichever version appears
first. Ordering retrieved chunks newest-first, or de-duplicating records before
prompting, is therefore not cosmetic — it determines the answer. Prompt-level
date labels alone did not help (previous study).

Observation, not a general claim: ten synthetic records, one line format, no
document boundaries, temperature 0 with a single sample per condition.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-rank-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-rank-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 304 and 305 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model
and server configuration, both arms at a ceiling or floor. The early decoy sits
at index 30 rather than at index 0 or immediately before the designated line, so
"earliest occurrence" is demonstrated at one offset only. Thinking-off is used
throughout; the thinking-on behaviour for this exact panel is untested (the
earlier thinking-on suite showed budget exhaustion instead of an answer).

Untested and worth doing next: an explicit precedence instruction
("use the first / use the most recently updated record"), a multi-hop variant
where the answer depends on a field that must be read from the earliest record,
and a thinking-on arm with enough budget to see whether deliberation can use
dates.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

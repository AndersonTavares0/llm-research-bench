# Recency metadata does not override positional selection

## Question and design

The position-conflict study showed that the thinking-off model returns the
**first** same-ID record in the context, not the designated one: with the target
at rank 1 it scored 10/10, and with the target moved to rank 9 it scored 0/10
while every answer emitted the rank-1 decoy.

That leaves a practical question for RAG: does an explicit, unambiguous
**recency** cue — a date attached to each candidate — override the first-occurrence
rule? This suite holds the nine dated codes constant across arms and moves only
the position of the newest one.

- **baseline** — newest record `updated 2025-08-21; field code is <designated>`
  at filler index 170 (rank 1), eight older records at rows 205–310.
- **recency_conflict** — the rank-1 slot holds the *second-newest* record
  (`updated 2024-12-08; field code is M1P6Z4`), the newest designated record moves
  to row 310 (rank 9), and the remaining seven older records fill rows 205–295.

Both arms use the same 340 filler rows, the same line template
`Record {id}: updated {date}; field code is {code}. `, the same nine
(date, code) pairs, the same instruction and query
(`Find the exact field code in the requested record...` /
`\nWhat is the code in record {id}?`), and the same ten targets (`K01`–`K10`).
There is no `ACTIVE`/`ARCHIVED`/`superseded` wording: the only precedence signal
is the date value itself, and only the newest record is correct.

Because both arms contain identical content in identical line templates, both
rendered to **7,252 tokens** with **zero** padding in all 20 rows.

Prediction: if the model compares dates, the challenge arm should still answer
the newest code at rank 9. If it selects by position, the challenge arm answers
the rank-1 record whose date is older.

Generation settings matched the previous thinking-off studies: Qwen3-1.7B Q4_K_M
(SHA-256 `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`),
llama.cpp 0.8.0-dev build 12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0,
cap 512, one client, no response constraint, seed 42, and
`chat_template_kwargs: {enable_thinking: false}` on both arms and on the
input-token count requests.

## Results

| Condition | Exact retrieval | Empty | Finish reason | Emitted code |
|---|---:|---:|---|---|
| Baseline (newest = rank 1) | **10/10** | 0 | 10 stop | designated, 10/10 |
| Recency conflict (newest = rank 9) | **0/10** | 0 | 10 stop | `M1P6Z4`, 10/10 |

Every challenge answer was `The code in record <id> is M1P6Z4.` — the rank-1
record, whose date (`2024-12-08`) is **older** than the designated record's
(`2025-08-21`). No answer emitted the newest code. All challenge responses
completed normally (`finish_reason=stop`, 16 completion tokens each), so the
result is a confident wrong answer rather than truncation.

Paired discordance: 0 improved / 10 worsened, exact two-sided McNemar
p = 0.001953125.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7252` with `usage_matches_input_tokens=True`, zero padding
in either arm, and no row contained non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
9,807.4 / 9,833.7 ms, p95 12,904.3 / 12,934.4 ms. Peak sampled VRAM 1,702.1 MiB
in both leases.

## Interpretation

On this task the no-reasoning answer path ignores explicit recency metadata and
returns the first matching record. Two independent manipulations now point the
same way:

- moving the designated code from rank 1 to rank 9 flipped 10/10 to 0/10;
- attaching unique, monotonically increasing dates to all nine candidates — with
  the correct answer unambiguously the newest — changed nothing.

So the earlier thinking-off 10/10 was not conflict resolution and not
date-based precedence; it was first-occurrence selection. Adding a
`updated <date>` field to every candidate is not sufficient to make this model
prefer the current value in a long, repetitive context.

This is a deployment-relevant failure mode for retrieval over records with
history: a retrieved chunk set that contains several versions of the same record
will be answered with whichever version appears first, regardless of its
timestamp, unless the prompt does something stronger than label dates.

Observation, not a general claim: ten synthetic records, one line format, no
document boundaries, no authority/confidence metadata, temperature 0 with a
single sample per condition.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-recency-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-recency-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 302 and 303 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model
and server configuration, and both arms at a ceiling or floor. The manipulation
moves the positions of all nine lines rather than only the newest, so position and
date are confounded in the challenge arm by construction — which is the point of
the test, but it cannot separate "first line wins" from "line at the 50% index
wins".

Untested and worth doing next: an explicit precedence instruction
("prefer the most recently updated record"), more than one recency level in the
same prompt, natural document chunks with headings, and a thinking-on variant to
see whether deliberation can use the dates when it is given budget.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

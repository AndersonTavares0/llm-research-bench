# Unlabeled same-record conflict: reasoning-budget exhaustion

## Question and design

The archived-conflict study (`needle-archived-conflict.md`) was ceiling-limited:
the `ACTIVE` / `ARCHIVED` labels resolved the conflict for the model. This study
removes every status label so that only **position/recency** distinguishes the
correct code from eight conflicting codes for the same record.

Ten fixed target records (`K01`–`K10`), 340 filler rows, target row at the 50%
position. Both arms share the identical instruction and query:

- instruction: `Find the exact field code in the requested record. Use only the
  context below; answer with the code and nothing else.`
- query: `\nWhat is the code in record {id}?`

Baseline contains exactly one line for the queried record:
`Record {id}: the exact field code is {value}.`
The challenge arm keeps that line in place and replaces eight later filler rows
(205, 220, 235, 250, 265, 280, 295, 310) with
`Record {id}: the exact field code is {old}.` — same record ID, eight different
codes, no `ACTIVE`, `ARCHIVED`, or `superseded` wording anywhere.

Both full payloads were measured through llama.cpp
`/v1/chat/completions/input_tokens`. Baseline prompts were 7,181 tokens; challenge
prompts were 7,149 before padding and were padded with 31 neutral `x` tokens to
the same 7,181. Every completion reported `usage.prompt_tokens=7181`; zero
mismatches across all 40 requests.

Generation settings for every run: Qwen3-1.7B Q4_K_M
(`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build12024 (`ddf48f85c`), ctx 8192, q8_0 K/V, temperature 0, one client,
no response constraint, seed 42.

Each 10-pair study ran as two five-pair leases (batches 0 and 1) under the existing
400-second lease policy.

## Results

Primary outcome is exact target-code match.

| Cap | Baseline | Challenge | Challenge `finish_reason=length` | Challenge empty content |
|---:|---:|---:|---:|---:|
| 512 | **10/10** | **3/10** | 7 | 7 |
| 1000 | **10/10** | **6/10** | 3 | 3 |

Per-case challenge outcomes:

| Case | Expected | Cap 512 | Cap 1000 |
|---|---|---|---|
| K01 | Q7M4K2 | correct (162 tok) | correct (162 tok) |
| K02 | P9V3D6 | correct (484 tok) | correct (484 tok) |
| K03 | R2C8W5 | truncated at 512 | truncated at 1000 |
| K04 | H6N1X4 | truncated at 512 | answered **M1P6Z4** (wrong) |
| K05 | B3T9L7 | truncated at 512 | truncated at 1000 |
| K06 | M5F2Z8 | truncated at 512 | correct (605 tok) |
| K07 | C8J4A1 | correct (323 tok) | correct (323 tok) |
| K08 | W1G7P3 | truncated at 512 | truncated at 1000 |
| K09 | D4Y6S2 | truncated at 512 | correct (727 tok) |
| K10 | X2L5N9 | truncated at 512 | correct (851 tok) |

Raising the cap rescued three cases (K06, K09, K10) and produced one confident
wrong answer (K04); three cases still exhausted 1,000 tokens. Paired discordance
512 → 1000 is 3 improved / 0 worsened (exact McNemar p = 0.25). Baseline vs
challenge at cap 1000 is 10/10 vs 6/10, 4 discordant pairs, all favouring baseline
(exact McNemar p = 0.125). With n=10 these are descriptive.

## Mechanism

The failures are not empty or malformed output from the server; they are
generation-budget exhaustion inside the model's reasoning phase. Every miss has:

- `finish_reason='length'`, `usage.completion_tokens` equal to the cap,
- `content=''`,
- a populated `message.reasoning_content` (1,903–4,149 characters).

The model detects the conflict and loops on how to resolve it. Reasoning tails
quote the competing codes and then stall, e.g. K09:

> "...then later A7C3M9, then F2R8K4, J5W1P6, N9B4T2, C6X2L8, V3H7Q1, and
> G8D5Y2. The user might be looking for the correct code, but the context
> doesn't specify which one is correct."

The one wrong answer (K04) resolved the conflict by **recency**, selecting the
last-listed decoy:

> "The context has multiple lines with different codes, but the exact code for
> K04 is the last one listed. So the answer is M1P6Z4."

Baseline completions never truncated: 10×`stop`, 121–182 completion tokens, with
short reasoning (438–668 characters). Challenge completions that did finish used
323–851 completion tokens.

Determinism check: K01, K02 and K07 produced identical completion-token counts at
both caps (162, 484, 323), consistent with greedy decoding reproducing the same
continuation — so the cap512 and cap1000 runs are not independent samples of the
same stochastic process.

## Context ceiling for this follow-up

ctx_size is 8192 and prompts are 7,181 tokens, so the largest completion budget
available without shortening the prompt is 1,011 tokens. 1,000 was therefore the
maximal budget test; testing whether the three remaining loops ever terminate
requires either a larger context or shorter prompts, not just a bigger cap.

## Reproducibility and safety

Raw artifacts (full prompts, generation requests/responses including
`reasoning_content`, input-token endpoint requests/responses, padding and count
provenance, campaign metadata, server logs, 1 Hz VRAM samples):

- `results/campaigns/gpu-lab-longctx-needle-unlabeled-conflict-b0/` (gen 293)
- `results/campaigns/gpu-lab-longctx-needle-unlabeled-conflict-b1/` (gen 295)
- `results/campaigns/gpu-lab-longctx-needle-unlabeled-conflict-cap1000-b0/` (gen 296)
- `results/campaigns/gpu-lab-longctx-needle-unlabeled-conflict-cap1000-b1/` (gen 297)

All four campaigns recorded `status=measured`, exit code 0, `cache_type_k/v=q8_0`,
and disjoint five-target halves covering all ten IDs. Each lease ended
`supervisor_stopped/restored`; production was re-verified with a real completion
(`recovered: OK`) and `/health` 200 after every lease, and the original experiment
config was restored (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`). Peak sampled
VRAM was 1,702.1 MiB in every run. One attempt (generation 294) was refused by the
existing boundary check (`foreign processes in subtree`); it consumed no results
and production recovered.

Latency (end-to-end client, 10 requests per batch): cap512 p50/p95
20,868/24,774 ms (b0) and 16,004/24,316 ms (b1); cap1000 p50/p95
23,155/38,259 ms (b0) and 16,031/36,882 ms (b1). Timing is descriptive only.

## Interpretation and limits

Within this fixed synthetic panel, an unlabeled same-record conflict is a genuine
failure mode for this model at deployment-relevant budgets: it produces no answer
at all in 7/10 cases at a 512-token cap and 3/10 at 1,000, and when it does resolve
the conflict it can choose the most recent rather than the correct value. The
dominant cause observed here is unbounded self-deliberation, not retrieval failure
of the context: the correct code is present, in the same position, in both arms.

Limits: ten synthetic records, one model/quantization/server build, one context
size, English, and prompts padded with neutral tokens. The panel cannot separate
"position/recency cue" from "number of conflicting candidates", and the 1,000-token
cap is bounded by ctx 8192 rather than chosen for adequacy. Nothing here establishes
behaviour on real documents, other models, or other context sizes.

Practical implication worth testing next: reasoning-mode models need either a
conflict-resolution instruction ("if several codes are listed, prefer the earliest
or the one marked current") or enough completion budget to finish reasoning; a
512-token cap silently converts hard conflicts into empty answers, which downstream
tooling may misread as a retrieval or server failure.

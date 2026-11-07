# Positional selection in same-record conflict retrieval

## Question and design

The thinking-off run of the unlabeled same-record conflict suite scored 10/10, but
the designated code always occupied the **first** of the nine same-ID lines. That
left an alternative explanation: the model may simply emit the first matching
record rather than resolve which value is correct.

This suite holds the multiset of nine same-ID codes constant and moves only the
designated code's position:

- **baseline** — designated code at filler index 170 (rank 1 of 9), eight decoys at
  rows 205–310.
- **position_conflict** — decoy `M1P6Z4` at index 170 (rank 1), the designated code
  at row 310 (rank 9), the remaining seven decoys at rows 205–295.

Both arms use the same 340 filler rows, the same line template
`Record {id}: the exact field code is {code}. `, the same instruction and query
(`Find the exact field code in the requested record...` /
`\nWhat is the code in record {id}?`), no `ACTIVE`/`ARCHIVED`/`superseded` wording,
and the same ten targets (`K01`–`K10`). Because the arms contain the same codes in
the same line template, both rendered to **7,153 tokens** with **zero** padding
(`baseline_padding` and `padding` both empty strings) — a stronger length control
than the earlier suites needed.

Prediction: first-occurrence selection → baseline 10/10, challenge 0/10;
last-occurrence selection → the reverse.

Generation settings were identical to the thinking-off study: Qwen3-1.7B Q4_K_M
(SHA-256 `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`),
llama.cpp 0.8.0-dev build 12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0,
cap 512, one client, no response constraint, seed 42, and
`chat_template_kwargs: {enable_thinking: false}` on both arms and on the
input-token count requests.

## Results

| Condition | Exact retrieval | Empty | Finish reason | Emitted code |
|---|---:|---:|---|---|
| Baseline (designated = rank 1) | **10/10** | 0 | 10 stop | designated, 10/10 |
| Position conflict (designated = rank 9) | **0/10** | 0 | 10 stop | `M1P6Z4`, 10/10 |

Every challenge answer named `M1P6Z4`, the code at rank 1, and no answer ever
emitted the designated code. All ten challenge responses were short and complete
(18 or 20 completion tokens, `finish_reason=stop`), so this is not truncation:
the model produced a confident wrong answer in the exact format the prompt asked
for. Baseline responses had the same shape (18–20 completion tokens).

Paired discordance was 0 improved / 10 worsened, exact two-sided McNemar
p = 0.001953125. All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7153` with `usage_matches_input_tokens=True`, and no row
contained non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1):
baseline-and-challenge pooled p50 9,577.4 / 9,592.9 ms, p95 12,648.3 /
12,677.4 ms. Peak sampled VRAM was 1,702.1 MiB in both leases.

## Interpretation

The earlier thinking-off 10/10 was **positional, not conflict resolution**. When
the designated value was first, the model returned it; when a decoy was first and
the designated value last, the model returned the decoy — the same
first-occurrence rule in both cases, scoring 10/10 and 0/10 respectively. On this
task the model does not appear to select among same-ID candidates by any evidence
in the context; it takes the first matching record.

This also re-reads the earlier suite results: the unlabeled-conflict thinking-off
score measured first-occurrence selection, and the thinking-on failures
(reasoning-budget exhaustion while deliberating which code was correct) show the
model does register the ambiguity when it reasons, but its no-reasoning answer
path does not resolve it.

Observation, not a general claim: these are synthetic prompts with a single line
format, no document boundaries, no metadata, and no instruction about precedence.
Real RAG inputs usually carry recency, authority, or relevance cues the model
could use, and this panel does not test them.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-position-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-position-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 300 and 301 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic (temperature 0) sample per
condition, single model and server configuration. The two arms differ in the
positions of all nine lines, not only the designated one, so the manipulation
moves the whole arrangement; a stricter next test would permute positions with
several offsets and include a "designated in the middle" arm. Ceiling and floor
effects now bracket the behaviour rather than characterise it, and nothing here
measures how the model behaves when the prompt supplies explicit precedence
instructions.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

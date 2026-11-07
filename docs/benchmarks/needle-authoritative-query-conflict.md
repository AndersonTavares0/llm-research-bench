# Naming the flag in the question helps, but only halfway

## Question and design

The previous suite showed that a single `authoritative: true` field among eight
`false` candidates is ignored when the question contains no selection cue: 0/10,
with every answer the earliest candidate.

The status-label suite, by contrast, reached 10/10 when the question said "active"
and the context lines said `status ACTIVE`. That difference is consistent with a
lexical account: the model matches a phrase from the question against the context
and returns the value attached to the match. This suite tests that account
directly by holding the JSON panel fixed and changing **only the question**.

- **baseline** — the `authoritative: true` candidate at filler index 170, eight
  `false` candidates at rows 205–310.
- **authoritative_query_conflict** — the same nine objects with the true candidate
  still at index 170 and the eight false ones moved to
  `range(20, 170, 19)` = 20, 39, 58, 77, 96, 115, 134, 153, all ahead of it.

Both arms use the identical body (byte-for-byte, asserted in tests). The only
difference from the flag suite is the trailing question:

- flag suite: `\nWhat is the code in record {id}?`
- this suite: `\nWhat is the code in record {id} whose authoritative flag is true?`

Both arms rendered to **7,228 tokens** with zero padding in all 20 rows.

Prediction under the lexical account: if the question now supplies the
discriminating cue, the challenge arm should reach 10/10 despite the true
candidate being last.

Generation settings: Qwen3-1.7B Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build 12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0, cap 512,
one client, no response constraint, seed 42, and
`chat_template_kwargs: {enable_thinking: false}` on both arms and on the
input-token count requests.

## Results

| Condition | Exact retrieval | Empty | Finish reason |
|---|---:|---:|---|
| Baseline (true candidate = rank 1) | **10/10** | 0 | 10 stop |
| Authoritative query conflict (true = rank 9) | **5/10** (batch 0: 4/10, batch 1: 6/10) | 0 | 10 stop |

Paired discordance: 5 improved / 0 worsened, exact two-sided McNemar
p = 0.0625 — a consistent direction, but not significant at α = 0.05 with this
sample size.

The misses were **not** systematic first-match failures this time:

| Case | Correct | Emitted | Challenge row of emitted code |
|---|---|---|---|
| K01 | Q7M4K2 | Q7M4K2 | — |
| K02 | P9V3D6 | `M1P6Z4` | 149 |
| K03 | R2C8W5 | `V3H7Q1` | 112 |
| K04 | H6N1X4 | H6N1X4 | — |
| K05 | B3T9L7 | B3T9L7 | — |
| K06 | M5F2Z8 | M5F2Z8 | — |
| K07 | C8J4A1 | C8J4A1 | — |
| K08 | W1G7P3 | `V3H7Q1` | 112 |
| K09 | D4Y6S2 | `A7C3M9` | 20 |
| K10 | X2L5N9 | `V3H7Q1` | 112 |

Only one miss (K09) returned the earliest candidate. The others returned decoys
from the middle or end of the candidate set. All responses were complete
(`finish_reason=stop`, 22 completion tokens) and phrased as confident assertions.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7228`, zero padding, and no non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
15,012.0 / 15,009.1 ms, p95 15,239.5 / 15,254.0 ms. Peak sampled VRAM
1,702.1 MiB in both leases.

## Interpretation

Naming the flag in the question moves the challenge arm from 0/10 to 5/10. That is
a real effect in the predicted direction, and it changes the *shape* of the
failure: with no cue the model always returned the earliest candidate, whereas
with a cue the misses scatter across the candidate set. So the question text does
reach the selection step.

But it is not the clean 10/10 the lexical account predicted, and it is much
weaker than the 10/10 obtained in the status-label suite where the question said
"active" and the lines said `status ACTIVE`. The most likely reason is that the
cue here is not a literal string match:

- question: `whose authoritative flag is true`
- context: `"authoritative": true`

The question inserts the words "flag is" between the key and the value, so no
contiguous span of the question appears in the context. In the status-label suite
the single word "active" did appear verbatim in exactly one line.

That reading is testable and is the next variant: quote the exact JSON fragment
in the question and see whether the challenge arm reaches 10/10.

Working summary of the mechanism across the last four suites:

| Cue | Where | Literal match in context? | Challenge exact |
|---|---|---|---:|
| none | — | — | 0/10 |
| `authoritative: true` | candidates only | n/a | 0/10 |
| "authoritative flag is true" | question | no | 5/10 |
| "active" | question | yes (`status ACTIVE`) | 10/10 |

Practical consequence unchanged for deployment: for models of this class the
authoritative record must be first in the context, or duplicates must be removed.
A question that names the discriminator helps but does not reliably rescue a
misordered context — half the time it still returns the wrong version.

Observation, not a general claim: ten synthetic records, one JSON line format, one
question wording, temperature 0 with a single sample per condition, thinking
disabled.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-authoritative-query-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-authoritative-query-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 321 and 322 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model and
server configuration. The challenge arm is at 5/10, so unlike the previous suites
this one is neither at a ceiling nor at a floor, which is why the paired test is
underpowered (five discordant pairs). The comparison with the status-label suite
confounds cue literalness with cue vocabulary and with the surrounding line
template, so it is a hypothesis about the mechanism, not a controlled
demonstration of it.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

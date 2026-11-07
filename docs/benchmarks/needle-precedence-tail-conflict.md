# Moving the precedence rule next to the query does not help either

## Question and design

The precedence study put an explicit selection rule in the head instruction —
`If several records share the requested ID, use the one with the most recent
date.` — and the model still answered the first same-ID record (0/10). Two
explanations remained:

1. the model cannot apply a selection rule across repeated candidates at all, or
2. the rule was too far from the query and lost to attention decay over ~7k
   tokens of filler.

This suite separates them by moving the same sentence to the **end** of the
prompt, immediately before the question, with the head instruction restored to
its plain form.

- **baseline** — newest record (`2025-08-21`, designated code) at filler index
  170 (rank 1); eight older dated records at rows 205–310.
- **precedence_tail_conflict** — rank-1 slot holds the second-newest record
  (`2024-12-08`, code `M1P6Z4`); the newest designated record moves to row 310
  (rank 9).

Both arms carry the identical tail

```
If several records share the requested ID, use the one with the most recent date.

What is the code in record {id}?
```

and the identical plain head instruction, the same 340 filler rows, the same
nine `(date, code)` pairs in the same line template
`Record {id}: updated {date}; field code is {code}. `, and the same ten targets
(`K01`–`K10`). The rule text is byte-identical to the head-rule suite, so both
variants also render to the same **7,269 tokens** with zero padding in all 20
rows.

Prediction: if the earlier failure was distance from the query, the tail variant
should recover the newest code at rank 9.

Generation settings: Qwen3-1.7B Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build 12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0, cap 512,
one client, no response constraint, seed 42, and
`chat_template_kwargs: {enable_thinking: false}` on both arms and on the
input-token count requests.

## Results

| Condition | Exact retrieval | Empty | Finish reason | Emitted code |
|---|---:|---:|---|---|
| Baseline (newest = rank 1) | **10/10** | 0 | 10 stop | designated, 10/10 |
| Precedence tail conflict (newest = rank 9) | **0/10** | 0 | 10 stop | `M1P6Z4`, 10/10 |

Every challenge answer was `The code in record <id> is M1P6Z4.` — the rank-1
record dated `2024-12-08`, which the rule says to ignore. All ten responses
completed normally (`finish_reason=stop`, 16 completion tokens each), so this is
a confident wrong answer, not truncation or an ignored-format artifact.

Paired discordance: 0 improved / 10 worsened, exact two-sided McNemar
p = 0.001953125.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7269`, zero padding, and no non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
9,883.7 / 9,880.4 ms, p95 12,969.5 / 12,973.0 ms. Peak sampled VRAM 1,702.1 MiB
in both leases.

## Interpretation

Instruction position is not the problem. The same sentence fails to change the
answer whether it sits at the head of the prompt or directly above the question,
and the failure is identical in kind and in emitted code.

That leaves the first explanation: with thinking disabled, this model does not
apply a multi-candidate selection rule to a repetitive context. It resolves the
query by locating the first matching record ID and returning that code. The rule
is present, syntactically well-formed, adjacent to the question, and simply not
executed over the nine candidates.

The full chain now reads:

| Study | Rule | Rule position | Challenge exact | Emitted |
|---|---|---|---:|---|
| `needle_recency_conflict` | none | — | 0/10 | rank-1 decoy |
| `needle_precedence_conflict` | "use most recent date" | head | 0/10 | rank-1 decoy |
| `needle_precedence_tail_conflict` | same sentence | immediately before query | 0/10 | rank-1 decoy |
| `needle_recency_conflict` thinking-on | none | — | 2/10 | last-match / empty |

Practical consequence is unchanged and now better supported: correctness has to
be engineered into the **context** — de-duplicate records before prompting, or
place the authoritative version first. Adding a selection rule to the prompt, in
any position, should not be relied on for this model class.

Observation, not a general claim: ten synthetic records, one line format, one
rule wording, temperature 0 with a single sample per condition, thinking
disabled.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-precedence-tail-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-precedence-tail-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 312 and 313 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model
and server configuration, both arms at a ceiling or floor. Only one rule wording
was tested; a system-role instruction, few-shot examples, or a structured
`candidates[]` input might behave differently. The rule is a single sentence in
prose; a schema-level field such as `"authoritative": true` on the correct record
is untested and is the more promising direction than more prompt wording.

Thinking-on for this exact tail variant is untested; the dated thinking-on run
showed budget exhaustion and last-match bias rather than rule application, so a
repeat there is low value compared with testing structured candidate metadata.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

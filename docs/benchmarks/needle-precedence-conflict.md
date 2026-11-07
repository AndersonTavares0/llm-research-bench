# A prompt-level precedence rule does not override first-match selection

## Question and design

The recency study showed that attaching `updated <date>` to all nine same-ID
records did not make the model prefer the newest one; it still answered the
record at rank 1. That leaves the practical question for deployment: can a
**prompt instruction** fix it?

This suite is the recency suite with one sentence added to the instruction, in
both arms:

- plain instruction: `Find the exact field code in the requested record. Use only
  the context below; answer with the code and nothing else.`
- ruled instruction: `Find the exact field code in the requested record. If
  several records share the requested ID, use the one with the most recent date.
  Use only the context below; answer with the code and nothing else.`

Everything else is byte-identical to `needle_recency_conflict`: 340 filler rows,
nine same-ID records each carrying a unique date, the newest record
(`2025-08-21`) holding the designated code, the other eight dated 2021-03-04
through 2024-12-08, and the same query `\nWhat is the code in record {id}?`.

- **baseline** — newest (designated) record at filler index 170, rank 1.
- **precedence_conflict** — the rank-1 slot holds the second-newest record
  (`2024-12-08`, code `M1P6Z4`); the newest designated record sits at row 310,
  rank 9.

Both arms rendered to **7,269 tokens** with zero padding in all 20 rows.

The comparison of interest is against the previous `needle_recency_conflict`
challenge arm, which used the identical prompts **without** the precedence
sentence and scored 0/10.

Generation settings: Qwen3-1.7B Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build 12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0, cap 512,
one client, no response constraint, seed 42, and
`chat_template_kwargs: {enable_thinking: false}` on both arms and on the
input-token count requests.

## Results

| Condition | Exact retrieval | Empty | Finish reason | Emitted code |
|---|---:|---:|---|---|
| Baseline (newest = rank 1, rule present) | **10/10** | 0 | 10 stop | designated, 10/10 |
| Precedence conflict (newest = rank 9, rule present) | **0/10** | 0 | 10 stop | `M1P6Z4`, 10/10 |

Adding the explicit rule changed nothing. All ten challenge answers returned the
rank-1 record, whose date (`2024-12-08`) is older than the designated record's
(`2025-08-21`), which is exactly the wrong choice under the stated rule. Answers
were short and complete (`finish_reason=stop`; 7 tokens when the model emitted a
bare code, 16 when it emitted a sentence).

Paired discordance: 0 improved / 10 worsened, exact two-sided McNemar
p = 0.001953125. Compared with the rule-free recency run, the challenge arm moved
0/10 → 0/10.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7269`, zero padding, and no non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
9,787.3 / 9,796.5 ms, p95 12,951.8 / 13,001.5 ms. Peak sampled VRAM 1,702.1 MiB
in both leases.

## Interpretation

For this model, at this size, with thinking disabled, an explicit precedence
instruction is not enough to make it prefer the most recently dated of nine
same-ID records. The instruction does not harm normal retrieval — the baseline
arm carries the same sentence and still scores 10/10 — so the failure is
specifically an inability to apply a selection rule across repeated candidates.

The four studies now form a consistent picture:

| Manipulation | Challenge exact | Emitted code |
|---|---:|---|
| Target moved to rank 9 (`position_conflict`) | 0/10 | rank-1 decoy |
| Unique dates, newest at rank 9 (`recency_conflict`) | 0/10 | rank-1 decoy |
| Designated index fixed, rank 2 (`rank_conflict`) | 0/10 | earlier decoy |
| Unique dates + explicit precedence rule (`precedence_conflict`) | 0/10 | rank-1 decoy |

Only the baseline arms, where the correct record is first, reach 10/10.

Practical consequence: for this class of model, correctness has to be engineered
into the **context**, not requested in the prompt. De-duplicate records before
prompting, or order candidates so the authoritative one comes first. Prompt-level
"prefer the newest / prefer the current one" instructions should not be relied
on.

Observation, not a general claim: ten synthetic records, one line format, one
instruction wording, temperature 0 with a single sample per condition, thinking
disabled.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-precedence-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-precedence-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 307 and 308 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. One earlier attempt
(generation 306) was refused at the container boundary
(`boundary_refused: foreign processes in subtree`) and recovered with the config
hash unchanged. After each successful lease the runner restored the original
experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model
and server configuration, both arms at a ceiling or floor. The rule wording is a
single phrasing; a stronger formulation, a system-role instruction, few-shot
examples, or a larger model might behave differently. Thinking-on is untested for
this panel (the earlier thinking-on suite failed by budget exhaustion rather than
by choosing the wrong record, which suggests deliberation does notice the
conflict — that variant with a large enough budget is the obvious next step).

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

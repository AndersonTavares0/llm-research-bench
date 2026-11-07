# Thinking mode turns first-match into last-match and often never finishes

## Question and design

Four thinking-off studies established that this model answers same-ID conflicts
with the **first** matching record, regardless of context position, dates, or an
explicit precedence rule. The obvious deployment question is whether enabling
the model's reasoning mode fixes that.

There was reason to hope so. On the earlier **undated** conflict panel
(`needle_unlabeled_conflict`, no dates, designated record at rank 1 of 9),
thinking-on at cap 1000 scored baseline 10/10 and challenge 12/20 — partial
conflict resolution, with successful answers spending 323–851 completion tokens.

This study repeats the **dated** panel (`needle_recency_conflict`, unchanged) with
thinking left at the model template default and the completion cap raised to the
largest value that still fits the 8,192-token context: **900** tokens
(7,248 prompt + 900 = 8,148).

- **baseline** — newest dated record (`2025-08-21`) holding the designated code
  at filler index 170, rank 1 of 9.
- **recency_conflict** — rank 1 holds the second-newest record
  (`2024-12-08`, code `M1P6Z4`); the newest designated record is at row 310,
  rank 9.

Both arms rendered to **7,248 tokens** with zero padding in all 20 rows. No
`chat_template_kwargs` were sent, so the template's default thinking mode was
active; 20/20 responses contained non-empty `reasoning_content`, confirming the
manipulation.

## Results

| Condition | Exact retrieval | Hit cap, empty answer | Completion tokens | Reasoning chars |
|---|---:|---:|---|---|
| Baseline (newest = rank 1) | **1/10** | 4 | 420–900 | 1,545–3,791 |
| Recency conflict (newest = rank 9) | **2/10** | 6 | 307–900 | 1,130–3,688 |

Half of all responses (10/20) exhausted the 900-token budget with
`finish_reason=length` and `content=''`. The rest answered confidently, mostly
wrongly. Paired discordance: 2 improved / 1 worsened.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
36.8 / 33.3 s, p95 40.1 / 37.2 s; campaign wall time 332 s and 323 s. Peak
sampled VRAM 1,702.1 MiB in both leases.

## Mechanism

The reasoning traces show what changed. With thinking off the model returns the
first occurrence silently. With thinking on it enumerates the candidates, then
converts **"latest" into "last in the context"**:

- K02 baseline, rank 1 correct, answered `M1P6Z4` (rank 9):
  *"the field code for K02 is the last one listed, which is M1P6Z4"*.
- K08 baseline answered `M1P6Z4` (rank 9) and justified it as
  *"based on the latest update in the provided context (2024-12-08)"* — the date
  is quoted correctly, but 2025-08-21 also exists in the same context and is
  never compared against it.
- K06 challenge answered correctly and justified it as
  *"based on the latest entry in the context (2025-08-21)"* — correct only because
  in that arm the designated record happens to be last.
- K03 baseline spent 3,266 characters of reasoning and never emitted an answer.

So the no-thinking **first-match** bias becomes a mostly **last-match** bias, with
the date field read but used as post-hoc justification for a positional choice.
The remaining failures are non-termination: the model keeps re-reading the
candidate set and never commits within the budget.

## Comparison across panels

| Panel | Thinking | Cap | Baseline exact | Challenge exact | Baseline completion tokens |
|---|---|---:|---:|---:|---|
| Undated conflict | on | 1000 | 10/10 | 12/20 | 121–182 |
| Dated conflict | on | 900 | 1/10 | 2/10 | 420–900 |
| Dated conflict | off | 512 | 10/10 | 0/10 | 16 |

Adding an `updated <date>` field to every candidate multiplies reasoning length
by roughly 3–6× and destroys the easy case. The model does not merely fail to use
the dates; their presence makes it deliberate about *which occurrence* to pick,
and that deliberation does not converge.

## Interpretation

For this model at this context length, enabling reasoning is not a fix for
same-ID conflict resolution: it regresses the baseline from 10/10 to 1/10,
converts first-match into last-match, and produces empty answers on half the
requests. The deployment conclusion from the thinking-off chain therefore stands
and is strengthened: correctness must be engineered into the context —
de-duplicate records, or order the authoritative record first. Do not rely on
either prompt instructions or the reasoning mode.

Observation, not a general claim: ten synthetic targets, one line format, one
instruction wording, temperature 0 with a single sample per condition.

## Limits

The cap is bounded by the 8,192-token context, so this study **cannot** separate
"needs more thinking budget" from "never converges" — at 7,248 prompt tokens only
~940 tokens remain. The 10/20 empty answers are all cap hits, and the answers that
did complete used 307–881 tokens, so the budget is clearly marginal rather than
absurd. A compact-context variant with a multi-thousand-token thinking budget is
the direct test of whether deliberation can compare dates at all; it is not run
here. One model, one server configuration, one instruction wording, one sample
per condition.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses (including
`reasoning_content`), input-token count requests/responses, padding provenance,
usage counts, campaign metadata, logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-recency-conflict-think-b0/`
- `results/campaigns/gpu-lab-longctx-needle-recency-conflict-think-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=900`,
`think=true`, `constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two
batches were disjoint five-target halves covering all ten targets. All 20 rows
had `matched_input_tokens = condition_input_tokens = usage_prompt_tokens = 7248`
with zero padding and no usage mismatch.

They ran as gpu-lab generations 309 and 311 under the existing 400-second
per-lease policy; both terminal attempts were `supervisor_stopped/restored`. One
earlier attempt (generation 310) was refused at the container boundary
(`boundary_refused: foreign processes in subtree`) and recovered with the config
hash unchanged. After each successful lease the runner restored the original
experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

# The first-match failure survives natural prose and document headings

## Question and design

Every earlier conflict study used one-line synthetic records
(`Record K01: updated 2025-08-21; field code is Q7M4K2.`) among repeated filler
sentences. That format is convenient but artificial, so the obvious objection is
that the observed first-match behaviour is an artifact of the line layout rather
than something a real retrieval prompt would show.

This suite re-renders the exact same nine dated records as multi-sentence
document chunks with Markdown headings, keeping the date logic and the ordering
logic of `needle_recency_conflict` unchanged. Only the record format differs.

Each of the nine candidates is now:

```
## Record K01 — audit note (2025-08-21)

The records team last updated this note on 2025-08-21. The field code for record K01 is Q7M4K2. No further changes were recorded.
```

- **baseline** — the newest chunk (`2025-08-21`, designated code) at filler index
  170 (rank 1); the eight older chunks at rows 205–310 in ascending date order.
- **prose_conflict** — the rank-1 slot holds the second-newest chunk
  (`2024-12-08`, code `M1P6Z4`); the newest designated chunk moves to row 310
  (rank 9); the other seven fill rows 205–295.

Instruction, query, filler, dates and codes are identical to the recency suite:
`Find the exact field code in the requested record. Use only the context below;
answer with the code and nothing else.` and `\nWhat is the code in record {id}?`.
The question contains no date, no "newest"/"current" cue, and no fragment of any
candidate line.

Because all nine chunks have the same byte length (they differ only in the 10-char
date and 6-char code), both arms are the same length and rendered to **7,558
tokens** with **zero** padding in all 20 rows.

Prediction: if the earlier first-match result were a line-format artifact, prose
chunks with headings should let the model use the dates and answer the newest
code at rank 9. If the mechanism is format-independent, the challenge arm answers
the rank-1 chunk.

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
| Prose conflict (newest = rank 9) | **0/10** | 0 | 10 stop | `M1P6Z4`, 10/10 |

All ten challenge answers were `The code in record <id> is M1P6Z4.` — the chunk
at rank 1, dated `2024-12-08`, which is older than the designated chunk's
`2025-08-21`. Every response was a complete sentence (`finish_reason=stop`, 16
completion tokens), so this is a confident wrong answer, not truncation.

Paired discordance: 0 improved / 10 worsened, exact two-sided McNemar
p = 0.001953125.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7558`, zero padding, and no non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
10,713.4 / 10,714.2 ms, p95 13,827.7 / 13,845.6 ms; campaign wall time 114 s /
113 s. Peak sampled VRAM 1,702.1 MiB in both leases.

## Interpretation

Changing the record format from one line to a headed multi-sentence paragraph
changed nothing. The dated-prose panel reproduces the dated-line panel exactly:
10/10 when the newest record is first, 0/10 when it is last, with the answer
always taken from rank 1.

| Panel | Format | Newest at rank 1 | Newest at rank 9 |
|---|---|---:|---:|
| `needle_recency_conflict` | one line per record | 10/10 | 0/10 |
| `needle_prose_conflict` | heading + 3-sentence chunk | 10/10 | 0/10 |

So the first-match behaviour is not an artifact of the synthetic line layout, of
the `Record <id>:` prefix, or of the absence of document structure. It survives
headings, prose, sentence-level context and repeated mention of the record ID.

This strengthens the deployment guidance rather than changing it: for a
thinking-off model of this size, correctness has to be engineered into the
retrieved context — de-duplicate records before prompting, or place the
authoritative version first. Attaching dates, status labels or headings to
duplicate versions does not make the model select the authoritative one.

Observation, not a general claim: one chunk template, one heading style, ten
synthetic targets, temperature 0 with a single sample per condition, thinking
disabled. The filler between chunks is still the synthetic repeated sentence, so
this varies the *record* format only, not the whole document corpus.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-prose-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-prose-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 325 and 326 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model
and server configuration, both arms at a ceiling or floor. Both arms use the same
nine chunks in different orders, so the manipulation is ordering only; chunk
count, chunk length and candidate set are held constant. Filler remains the
repeated synthetic sentence, so the corpus as a whole is not natural.

Untested and worth doing next: fewer duplicate versions (two rather than nine),
so the conflict looks like a normal top-k retrieval result; real multi-field
documents where the answer requires reading a field that is not repeated across
versions; and the same prose panel with thinking enabled and a larger budget.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

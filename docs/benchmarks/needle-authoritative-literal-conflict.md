# Verbatim question tokens decide retrieval; paraphrase does not

## Question and design

Three suites now differ only in how the question refers to the discriminating
field, on an identical JSON candidate panel:

| Question wording | Overlap with context | Challenge exact |
|---|---|---:|
| `What is the code in record {id}?` | none | 0/10 |
| `... whose authoritative flag is true?` | none (words inserted) | 5/10 |
| `... in the line containing "authoritative": true?` | verbatim fragment | **10/10** |

This suite is the third row. It is the flag suite with one change: the question
quotes the exact JSON fragment that appears in exactly one candidate line.

- **baseline** — `{"record": "K01", "code": "Q7M4K2", "authoritative": true}` at
  filler index 170, eight `false` candidates at rows 205–310.
- **authoritative_literal_conflict** — the same nine objects, true candidate still
  at index 170, eight `false` candidates at `range(20, 170, 19)` = 20, 39, 58, 77,
  96, 115, 134, 153, all ahead of it.

The question is
`\nWhat is the code in record {id} in the line containing "authoritative": true?`.
The fragment `"authoritative": true` therefore occurs twice in the prompt: once in
the single true candidate, once in the question. Tests assert both counts and that
the body is byte-identical to the flag suite.

Both arms rendered to **7,232 tokens** with zero padding in all 20 rows.

Prediction under the lexical account: with a verbatim fragment available, the
challenge arm should reach 10/10 despite the true candidate being last.

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
| Authoritative literal conflict (true = rank 9) | **10/10** | 0 | 10 stop |

Paired discordance: 0 improved / 0 worsened, McNemar p = 1.0. This is a ceiling in
the challenge arm, which is exactly what the lexical account predicts for a
verbatim cue.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7232`, zero padding, and no non-empty `reasoning_content`.
Completion lengths were 23–32 tokens, all `finish_reason=stop`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
15,223.8 / 15,326.1 ms, p95 15,510.9 / 15,456.8 ms. Peak sampled VRAM
1,702.1 MiB in both leases.

## Interpretation

The three-way comparison is a controlled demonstration, because the candidate
panel, the row order, the context length and the sampling settings are identical
across all three suites; only the question string changes.

- no reference to the flag → the earliest candidate wins (0/10);
- a paraphrase that never appears in the context → scattered errors, 5/10;
- a verbatim fragment that appears in exactly one line → 10/10.

So the thinking-off answer path is doing **string matching between the question and
the context**, not applying a selection rule over metadata. When the question
contains a span that occurs in exactly one candidate, retrieval is reliable
regardless of where that candidate sits. When it does not, position decides.

This also reinterprets the earlier status-label result (10/10 with `active` in the
question) and the archived-conflict result: those were verbatim-token successes,
not label semantics.

Practical consequence for retrieval on models of this class:

- put the authoritative record first, or de-duplicate before prompting — this is
  the only reliable fix, because it does not depend on the question wording;
- if a question must disambiguate, quote a literal value from the target record
  (`"authoritative": true`, the exact status token, the exact version string)
  rather than describing it ("the most recent", "the authoritative one", "the
  current version");
- adding metadata fields to candidates is useless on its own — the field only
  helps once the question quotes it.

Observation, not a general claim: ten synthetic records, one JSON line format, one
question wording per arm, temperature 0 with a single sample per condition,
thinking disabled. A ceiling here shows the cue is sufficient, not that the model
is generally reliable on long contexts.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-authoritative-literal-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-authoritative-literal-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 323 and 324 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model and
server configuration, both arms at a ceiling. Only one verbatim fragment was
tested; whether an unrelated literal string works equally well, and whether the
effect survives natural prose (where a "line" is a paragraph and the fragment is
not JSON), is untested. All evidence is at ~7.2k tokens in a single-line-per-record
format with no document boundaries.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

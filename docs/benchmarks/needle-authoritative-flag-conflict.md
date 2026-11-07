# A structured authoritative flag does not override first-match selection

## Question and design

The status-label study showed that the model's apparent success with
`status ACTIVE` / `status ARCHIVED` depended on the *question* containing the
word "active": when the question only asked for "the value", the same label
arrangement scored 2/10 and the model returned the earliest archived candidate.

Two explanations remained for that failure. Either the model cannot use status
semantics at all unless the question echoes the label, or prose status words are
simply too weak a signal in a long repetitive context. This suite replaces the
prose label with an explicit, machine-readable field — a JSON object with a
boolean `authoritative` key — and asks a question that contains no selection
word at all.

Each of the nine candidates is one line:

```
{"record": "K01", "code": "Q7M4K2", "authoritative": true}
{"record": "K01", "code": "A7C3M9", "authoritative": false}
...
```

- **baseline** — the `authoritative: true` candidate at filler index 170,
  eight `authoritative: false` candidates at rows 205, 220, 235, 250, 265, 280,
  295, 310.
- **authoritative_flag_conflict** — the same nine objects, but the true candidate
  stays at index 170 while the eight false ones move to
  `range(20, 170, 19)` = 20, 39, 58, 77, 96, 115, 134, 153, i.e. all ahead of it.

The instruction is `Find the code in the requested record. Use only the context
below; answer with the code and nothing else.` and the query is
`\nWhat is the code in record {id}?`. Neither mentions "authoritative", "true",
"false", "current" or any other selection cue; tests assert this.

Both arms contain the same nine JSON objects, differ only in row placement, and
are byte-identical in length. Both rendered to **7,223 tokens** with zero padding
in all 20 rows.

Prediction: if the model can apply a structured selection field, the challenge
arm should still answer the single `authoritative: true` code. If the failure in
the status-label study was lexical rather than semantic, this structured field
should not help either.

Generation settings: Qwen3-1.7B Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build 12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0, cap 512,
one client, no response constraint, seed 42, and
`chat_template_kwargs: {enable_thinking: false}` on both arms and on the
input-token count requests.

## Results

| Condition | Exact retrieval | Empty | Finish reason | Emitted code |
|---|---:|---:|---|---|
| Baseline (true candidate = rank 1) | **10/10** | 0 | 10 stop | designated, 10/10 |
| Authoritative flag conflict (true = rank 9) | **0/10** | 0 | 10 stop | `A7C3M9`, 10/10 |

Every challenge answer returned `A7C3M9`, the `authoritative: false` candidate at
filler index 20 — the earliest candidate in the context, and the exact code that
the status-label challenge arm also returned in 7 of 8 misses. All responses were
short and complete (`finish_reason=stop`, 17 completion tokens), so this is a
confident wrong answer, not truncation.

Paired discordance: 0 improved / 10 worsened, exact two-sided McNemar
p = 0.001953125.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7223`, zero padding, and no non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
14,869.1 / 14,863.2 ms, p95 15,172.2 / 15,125.9 ms. Peak sampled VRAM
1,702.1 MiB in both leases.

## Interpretation

A single `authoritative: true` field among eight `false` candidates is a much
stronger and less ambiguous signal than a prose status word, and it is ignored.
Combined with the previous study, the mechanism is now well supported:

- the thinking-off answer path locates a token from the **question** in the
  context and returns the value attached to it;
- when the question contains no distinguishing token, it returns the **earliest**
  matching record;
- metadata attached to the candidates — dates, prose status words, structured
  boolean flags — contributes nothing to the choice.

| Study | Signal on candidates | Question echoes it? | Challenge exact |
|---|---|---|---:|
| `needle_archived_rank_conflict` | ACTIVE/ARCHIVED, active last | yes ("active") | 10/10 |
| `needle_status_label_conflict` | ACTIVE/ARCHIVED, active last | no | 2/10 |
| `needle_authoritative_flag_conflict` | JSON `authoritative` true/false | no | 0/10 |
| `needle_recency_conflict` | unique dates, newest last | no | 0/10 |
| `needle_precedence_conflict` | dates + prose rule at head | rule only | 0/10 |
| `needle_precedence_tail_conflict` | dates + prose rule before query | rule only | 0/10 |

The 10/10 cases are all ones where the question supplies the discriminating
token. Nothing else has worked.

Practical consequence for retrieval pipelines on models of this class:
correctness must be engineered into the **context**. De-duplicate records before
prompting, or order the authoritative record first. Adding `authoritative`,
`status`, `updated`, or `superseded` fields to retrieved chunks is not a
substitute, and neither is a prompt rule — even a structured boolean that a
larger model would use directly.

Observation, not a general claim: ten synthetic records, one JSON line format, no
document boundaries, temperature 0 with a single sample per condition, thinking
disabled.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-authoritative-flag-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-authoritative-flag-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 319 and 320 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model
and server configuration, both arms at a ceiling or floor. Only one representation
of the boolean was tested (`true`/`false` JSON literals, no `"yes"`, no numeric
flags, no schema explanation). The question deliberately avoids the word
"authoritative", so this measures the no-cue case; whether naming the field in the
question rescues it is untested and is the natural next variant.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

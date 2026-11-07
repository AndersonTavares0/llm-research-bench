# A categorical status label overrides first-match selection

## Question and design

Every manipulation tested so far failed to beat first-match selection: moving the
designated record later, attaching unique dates, and adding an explicit
precedence rule at the head or at the tail of the prompt all produced 0/10 with
the rank-1 decoy.

The one earlier success was the `needle_archived_conflict` suite, which scored
10/10 with an `ACTIVE`/`ARCHIVED` vocabulary. Re-reading that builder showed why
it could not be interpreted: the `ACTIVE` record sat at filler index 170 and all
eight `ARCHIVED` records were placed at rows 205–310, i.e. **after** it. That arm
was therefore also consistent with plain first-match selection.

This suite removes the confound by holding the nine rows fixed and moving only
their order.

- **baseline** — `ACTIVE` record at filler index 170 (rank 1); eight `ARCHIVED`
  records at rows 205, 220, 235, 250, 265, 280, 295, 310.
- **archived_rank_conflict** — the same `ACTIVE` record at index 170, but all
  eight `ARCHIVED` records moved to rows 20, 39, 58, 77, 96, 115, 134, 153, so
  every `ARCHIVED` line precedes the `ACTIVE` one.

Both arms contain the identical nine lines with identical text — only their
positions differ — so both render to the same length and, in the event, to
**7,234 tokens** with zero padding in all 20 rows. Line templates:

```
Record {id}: ACTIVE revision 2025; current field code is {code}. 
Record {id}: ARCHIVED revision {2017..2024}; superseded field code was {code}. 
```

Instruction and query are unchanged from the earlier archived suite:
`Find the current field code for the requested record...` and
`\nWhat is the active field code in record {id}?`

Prediction: first-match selection gives 10/10 in the baseline and 0/10 in the
challenge, answering the earliest `ARCHIVED` code.

Generation settings: Qwen3-1.7B Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build 12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0, cap 512,
one client, no response constraint, seed 42, and
`chat_template_kwargs: {enable_thinking: false}` on both arms and on the
input-token count requests.

## Results

| Condition | Exact retrieval | Empty | Finish reason | Emitted code |
|---|---:|---:|---|---|
| Baseline (ACTIVE = rank 1) | **10/10** | 0 | 10 stop | designated, 10/10 |
| Archived rank conflict (ACTIVE = rank 9) | **10/10** | 0 | 10 stop | designated, 10/10 |

The prediction failed in the informative direction. With eight `ARCHIVED`
records ahead of it, the model still returned the `ACTIVE` code for every target,
in the same sentence form as the baseline
(`The active field code in record <id> is <code>.`, 18 completion tokens,
`finish_reason=stop`).

Paired discordance: 0 improved / 0 worsened, McNemar p = 1.0. This is a ceiling
result — it cannot estimate a success rate, only show that the manipulation does
not degrade performance on this panel.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7234`, zero padding, and no non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
14,930.9 / 14,963.4 ms, p95 15,248.2 / 15,261.5 ms. Peak sampled VRAM 1,702.1 MiB
in both leases.

## Interpretation

This is the first manipulation in the series that survives rank reversal. The
contrast is now sharp:

| Signal on the correct record | Rank of correct record | Exact |
|---|---:|---:|
| none (unlabeled same-ID) | 9 | 0/10 |
| unique date, newest correct | 9 | 0/10 |
| unique date + prose rule (head) | 9 | 0/10 |
| unique date + prose rule (tail) | 9 | 0/10 |
| `ACTIVE` vs `ARCHIVED` status word | 9 | **10/10** |

A categorical status word is usable by this model where a date comparison and a
prose selection rule are not. Two readings were consistent with this result:

1. **Label semantics** — the model treats `ACTIVE` as the authoritative marker
   and prefers that row.
2. **Lexical anchoring** — the query asks for "the *active* field code" and the
   `ACTIVE` line is the only line containing that word, so the answer may be a
   token match rather than a judgement about status.

**Follow-up resolved this in favour of lexical anchoring.**
`needle_status_label_conflict` reuses the same `ACTIVE`/`ARCHIVED` vocabulary but
in a template the question does not echo (`Record {id}: status ACTIVE; value is
{code}.` with the query `What is the value in record {id}?`). With the same rank
reversal it scores **2/10**, and 7 of the 8 misses return the earliest `ARCHIVED`
code. So the 10/10 above is not evidence that the model reads status; it is
evidence that the model matches a word from the question against a line.

The practical recommendation is therefore unchanged and narrower than it first
appeared: put the authoritative record first, or de-duplicate before prompting.
A status vocabulary helps only when the question itself names the discriminator.

Observation, not a general claim: ten synthetic records, one line format, one
status vocabulary, temperature 0 with a single sample per condition, thinking
disabled.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-archived-rank-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-archived-rank-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 315 and 316 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. An earlier attempt
(generation 314) was refused at the container boundary
(`boundary_refused: foreign processes in subtree`) and recovered with the config
hash unchanged. After each successful lease the runner restored the original
experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model
and server configuration, both arms at ceiling. Because the challenge arm also
scored 10/10, this design cannot show *how* the label is used — only that this
particular combination of status words, line templates and query wording is not
degraded by rank reversal.

The lexical-anchoring confound is the main open question. It is directly
testable: give every row the same template with only the status word differing
(`Record {id}: status ACTIVE; value {code}.` vs `status ARCHIVED`) and ask
`What is the value in record {id}?`, so that neither `ACTIVE` nor `ARCHIVED`
appears in the question. If the answer is still correct, the model is using the
label; if it reverts to first-match, the earlier success was query-lexical.

Also untested: whether an unrelated categorical marker (`primary`/`secondary`,
`v2`/`v1`) works, whether two competing `ACTIVE` rows break the behaviour, and a
thinking-on arm on this panel.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

# The status-label success was lexical matching, not label use

## Question and design

`needle_archived_rank_conflict` showed that an `ACTIVE`/`ARCHIVED` vocabulary
survived rank reversal: with all eight `ARCHIVED` rows ahead of the `ACTIVE` one,
the model still scored 10/10. That result had two readings — the model prefers
the record marked authoritative, or the question simply contained the word
"active" that appears in exactly one line.

This suite removes the lexical overlap. Every row uses the same template and only
the status word differs:

```
Record {id}: status ACTIVE; value is {code}. 
Record {id}: status ARCHIVED; value is {code}. 
```

and the question never mentions a status:

```
Find the value in the requested record. Use only the context below; answer with the value and nothing else.

Context:
<340 filler rows with nine same-ID records>

What is the value in record {id}?
```

The words `active`, `archived` and `current` appear nowhere in the instruction or
the query; `value`, `record` and `code` appear in both line types equally.

- **baseline** — `ACTIVE` record at filler index 170 (rank 1); eight `ARCHIVED`
  records at rows 205, 220, 235, 250, 265, 280, 295, 310.
- **status_label_conflict** — the same `ACTIVE` record at index 170, all eight
  `ARCHIVED` records at rows 20, 39, 58, 77, 96, 115, 134, 153.

Both arms hold the identical nine lines and differ only in order, so they render
to the same length: **7,159 tokens**, zero padding in all 20 rows.

Prediction: if the earlier 10/10 came from label semantics, the challenge arm
stays at 10/10. If it came from the question echoing "active", the challenge arm
falls back to first-match selection and answers the earliest `ARCHIVED` code.

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
| Status label conflict (ACTIVE = rank 9) | **2/10** | 0 | 10 stop | earliest `ARCHIVED`, 7/8 misses |

Per-batch challenge accuracy was 4/10 (batch 0) and 0/10 (batch 1); the pooled
figure is 2/10.

Misses returned the earliest `ARCHIVED` row, `A7C3M9` at index 20, in 7 of 8
cases; one miss (`K03`) returned the second `ARCHIVED` row, `F2R8K4` at index 39.
The two hits (`K06`, `K09`) returned the designated value. All responses completed
normally (`finish_reason=stop`, 16 or 18 completion tokens), so these are
confident answers rather than truncation.

Paired discordance: 0 improved / 8 worsened, exact two-sided McNemar
p = 0.0078125.

All 20 rows had `matched_input_tokens = condition_input_tokens =
usage_prompt_tokens = 7159`, zero padding, and no non-empty `reasoning_content`.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): p50
14,632.3 / 14,639.9 ms, p95 14,936.0 / 14,906.8 ms. Peak sampled VRAM 1,702.1 MiB
in both leases.

## Interpretation

The status label is not used. With the same vocabulary, the same rank reversal
and a question that does not echo the label, the model reverts to exactly the
behaviour seen in every other unlabeled conflict study: it returns the earliest
matching record.

| Signal on the correct record | Question echoes the label? | Rank of correct record | Exact |
|---|---|---:|---:|
| `ACTIVE`/`ARCHIVED` | yes ("the active field code") | 9 | 10/10 |
| `ACTIVE`/`ARCHIVED` | no ("the value in record …") | 9 | **2/10** |
| unique date, newest correct | no | 9 | 0/10 |
| prose rule at head or tail | rule only | 9 | 0/10 |

The difference between the first two rows is the whole finding: the 10/10 was
token matching between the question and one line of the context, not a judgement
about which record is current.

Mechanistically this is consistent with everything else measured on this model
size: the answer path locates the query's distinguishing token and returns the
value attached to it. When the query has no distinguishing token, the first
matching record wins. Dates and prose rules add no usable signal.

Deployment consequence, now with a clean causal story:

- de-duplicate records before prompting, or order the authoritative record first;
- do not rely on `status: active`, dates, or "prefer the newest" instructions to
  select among repeated records;
- a status word only helps when the user's own question names it, which is not
  something a retrieval pipeline can count on.

Observation, not a general claim: ten synthetic targets, one line template, one
status vocabulary, temperature 0 with a single sample per condition, thinking
disabled.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-status-label-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-status-label-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; the two batches were
disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 317 and 318 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease the runner
restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model
and server configuration. The challenge arm is between floor and ceiling (2/10),
so the effect is measured rather than clipped, but with n=10 per condition the
confidence interval is wide.

The two hits are not explained. `K06` and `K09` are in different batches, and
both answered correctly while their batch-mates did not, so this is not a
batch-level artifact; a per-case sample or a temperature sweep would be needed to
say whether it is noise or a content effect.

Untested: whether a *different* categorical vocabulary with no lexical path at
all (numeric ids, `v2`/`v1`, `primary`/`secondary`) behaves the same, and whether
an explicit structured field such as `"authoritative": true` in a JSON candidate
list is treated differently from prose. Given the pattern so far, the structured
form is the more promising direction than any further prompt wording.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

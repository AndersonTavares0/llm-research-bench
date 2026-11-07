# Archived-conflict retrieval at long context

## Question and design

When the requested record has one labelled active value and several later,
explicitly archived values for the *same* record ID, does exact retrieval of the
active value degrade compared with the same record with no archived values?

Ten fixed target records (`K01`–`K10`) were each run in both conditions. The
target row stayed at the 50% filler-row position and read
`Record <id>: ACTIVE revision 2025; current field code is <code>.` in both arms.
The challenge arm replaced eight later filler rows with
`Record <id>: ARCHIVED revision 2017…2024; superseded field code was <other>.`
for the same record ID and a conflicting code. The instruction and query were
identical in both arms: `Find the current field code for the requested record…`
and `What is the active field code in record <id>?`.

Condition order alternated within target pairs, and the targets were split
across two five-pair leases to fit the existing lease deadline.

## Token matching

Both full chat-completion payloads were measured through llama.cpp's
`/v1/chat/completions/input_tokens` endpoint, which renders the same chat
template as completion. Here the challenge arm was the *longer* one (archived
rows tokenize slightly longer than the filler rows they replace), so the runner
was changed to pad whichever arm is shorter to the common maximum. The baseline
arm received 39 neutral `x` tokens before the final query; the challenge arm
received none. Both arms were 7,230 rendered tokens, and every completion's
`usage.prompt_tokens` was checked against that count.

Generation settings were identical to the earlier retrieval suites: Qwen3-1.7B
Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0, cap 512,
one client, no response constraint, seed 42. Exact target-code match is the
primary outcome.

## Results

| Condition | Exact retrieval | Empty | Archived code in output | Input-token mismatches |
|---|---:|---:|---:|---:|
| Active record only | **10/10** | 0 | 0 | 0 |
| Active + 8 archived conflicts | **10/10** | 0 | 0 | 0 |

All ten pairs had equal 7,230-token inputs and matching `usage.prompt_tokens`.
All outputs contained the active code and none contained any archived code.
Paired discordance was 0 improved / 0 worsened; the exact two-sided McNemar
result is p=1.0. This describes the observed fixed panel only.

Both leases sampled peak VRAM at 1,702.1 MiB. Each lease made ten completion
requests (five pairs): batch 0 p50/p95 latency 15,546/19,840 ms; batch 1
14,382/19,449 ms. Timing is descriptive only; small n, request order and
prefix-cache reuse limit interpretation.

One behavioural difference from the earlier unrelated-decoy suite: answers here
were full sentences (`The active field code in record K03 is **R2C8W5**.`)
rather than bare codes, in both arms. `exact_match` still holds because the
expected code is present, but strict "answer with the code and nothing else"
adherence is not demonstrated for this prompt wording.

## Reproducibility and safety

Raw artifacts (full prompts, generation requests/responses, token-count
endpoint requests/responses, padding provenance, usage, campaign metadata,
server logs, 1 Hz VRAM samples):

- `results/campaigns/gpu-lab-longctx-needle-archived-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-archived-conflict-b1/`

Both campaigns recorded `status=measured`, exit code 0, and disjoint five-ID
batches covering all ten targets. They ran as gpu-lab generations 291 and 292
under the existing 400-second per-lease policy; both terminal attempts were
`supervisor_stopped/restored`, and production was checked with a real completion
(`recovered: OK`, `active_requests=0`) after each. The original experiment
config was restored with SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`.

Three earlier attempts did not produce data and were recovered by the
controller: generations 288 and 290 were refused at the container boundary
(`boundary_refused: foreign processes in subtree`), and generation 289 failed
closed because the challenge prompt was longer than the baseline and the runner
at that time could only pad upward. That failure drove the pad-the-shorter-arm
change; no experiment configuration or safety control was altered.

## Interpretation and limits

Explicit `ACTIVE revision 2025` / `ARCHIVED revision <year>; superseded` labels
were sufficient for this model to return the active code in all ten synthetic
cases, even though the archived values appeared *later* in the context. This
does not show that the model resolves conflicts in general: the labels are
unambiguous and adjacent to each value, the panel is ten fixed synthetic
targets, and both arms are at ceiling.

The next discriminating variant is to remove or weaken the status labels so the
only cue is position/recency; that separates "reads the status field" from
"prefers the last matching value". Also untested: conflicts inside natural
documents, conflicting values with no status metadata, and cases where the
active row appears *after* the archived rows.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

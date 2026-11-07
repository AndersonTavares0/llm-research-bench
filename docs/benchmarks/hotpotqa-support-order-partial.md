# HotpotQA support-order pilot (interrupted)

## Status and protocol

This is a partial descriptive pilot, **not** the planned 100-question study.
Three of twenty planned batches completed: 15 paired questions (30 model
responses) from the pinned HotpotQA `distractor` validation fixture. The fixture
has 50 bridge and 50 comparison questions, all labeled hard; each prompt retains
all ten supplied candidate passages. Conditions place supporting passages
first or last, preserving within-group order. Input lengths were exactly matched
with the serving tokenizer and request order alternated. Scores are normalized
answer exact match (EM), supporting-title F1, and joint exact (both answer and
complete support-title set correct).

HotpotQA is closed-context multi-hop QA, not live retrieval or a version-history
conflict benchmark. These first 15 items are not a representative estimate and
the experiment stopped before its planned sample size.

## Observed outcomes

| Batch | Condition | n | Answer EM | Mean support-title F1 | Joint exact |
|---|---|---:|---:|---:|---:|
| b00 | Support first | 5 | 1/5 | 0.5333 | 0/5 |
| b00 | Support last | 5 | 1/5 | 0.6667 | 0/5 |
| b01 | Support first | 5 | 0/5 | 0.7267 | 0/5 |
| b01 | Support last | 5 | 0/5 | 0.3667 | 0/5 |
| b02 | Support first | 5 | 0/5 | 0.6000 | 0/5 |
| b02 | Support last | 5 | 0/5 | 0.6000 | 0/5 |

Across the 30 responses, reported usage tokens matched the paired target count;
there were no usage-token mismatches. All three batch artifacts carry the
expected fixture SHA-256:
`661718dde69699e74a5bd32713ff794b69147ff4ffdeb95bb93130c410ba4a23`.

## Raw artifacts

Each linked batch directory contains the raw capability JSON, campaign summary,
metadata and run log. The b01 and b02 local copies were checked file-by-file
against the remote campaign trees; all seven files in each matched hashes.

- [Batch b00](../../results/campaigns/gpu-lab-longctx-hotpotqa-support-order-b00/) — raw results SHA-256 `677096df26cb59bec21e4cdf5a29c713af738d594a0422004dd2922966b8515a`
- [Batch b01](../../results/campaigns/gpu-lab-longctx-hotpotqa-support-order-b01/) — raw results SHA-256 `70bdda93a0f43fc9b633c98fb9a1f0b0b66e73d7e6e49961a631127700890b6c`
- [Batch b02](../../results/campaigns/gpu-lab-longctx-hotpotqa-support-order-b02/) — raw results SHA-256 `d28e49131591dee58596fde855b1fa71026a32d630728f2d53b2e9276543d619`

## Stop reason

No further GPU batches were launched after the authoritative production-recovery
verifier's real completion check returned HTTP 500. The production alias
`qwen3.5:4B` referenced the absent file
`/models/Qwen3.5-4B-Q4_K_M-MTP.gguf`. Controller state and the health endpoint
alone were insufficient to establish recovery. That was the study's stop decision
at the time, not a statement about current production status; the historical GGUF
pathname may be obsolete, and current deployment routing remains unverified. No
result here supports a general ordering effect.

## Subsequent operational status (2026-11-07)

A historical read-only check on 2026-11-07 found the authoritative verifier
passing for production generation 347 with zero active leases. The verifier SHA-256 was
`74157aec20bb160dce1361b645d33a87f48bcf03ff53b302203672480cc292e0`; its real
completion check through alias `qwen3.5:4B` succeeded. However, the previously
reported file `/models/Qwen3.5-4B-Q4_K_M-MTP.gguf` still tested absent. The
path observation is not evidence of current production failure: the deployment
architecture or alias-to-model mapping may have changed. This environment could
not verify the current deployed route or model mapping, and the 2026-11-07 check
does not establish today's state. No additional study batch was launched. Do not
resume GPU work until an authorized owner-side source confirms the current route,
model mapping, and recovery procedure. The 15-pair pilot remains incomplete and
descriptive.

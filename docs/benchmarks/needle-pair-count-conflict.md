# Two duplicates are already risky, and adjacency decides how risky

## Question and design

The prose study showed that nine duplicate versions of one record, rendered as
headed document chunks, still produce first-match selection: baseline 10/10,
challenge 0/10. That panel confounds two things — how many duplicates there are
and how far apart they sit. Real retrieval usually returns **two** versions of a
record, and they are often adjacent chunks from the same document.

This study holds the content fixed at two versions and varies only their
placement:

- **adjacent_pair_conflict** — newest chunk at filler index 170, older chunk at
  171.
- **distant_pair_conflict** — newest chunk at filler index 170, older chunk at
  310.

In both suites the baseline arm puts the newest (`2025-08-21`, designated) chunk
first and the challenge arm swaps the two, so the older chunk
(`2024-12-08`, code `M1P6Z4`) comes first and the designated chunk second. Both
arms of both suites use the same 340 filler rows, the same chunk template
(`## Record {id} — audit note ({date})` plus two prose sentences), the same
instruction and query (`Find the exact field code in the requested record...` /
`\nWhat is the code in record {id}?`), and the same ten targets (`K01`–`K10`).
No `ACTIVE`/`ARCHIVED` wording, no precedence sentence: the date is the only
precedence signal.

Each suite rendered to **7,271 tokens** with zero padding in all 20 rows, and the
two suites are token-identical to each other — only the filler index of the older
chunk differs.

Predictions: if the model compares the two dates, both challenge arms should be
10/10. If it takes the first chunk, both should be 0/10. A difference between the
two arms measures whether adjacency helps it notice the conflict at all.

Generation settings: Qwen3-1.7B Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build 12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0, cap 512,
one client, no response constraint, seed 42, and
`chat_template_kwargs: {enable_thinking: false}` on both arms and on the
input-token count requests.

## Results

| Suite | Condition | Exact retrieval | Emitted code |
|---|---|---:|---|
| adjacent | baseline (newest first) | **10/10** | designated, 10/10 |
| adjacent | challenge (newest second, index 171) | **7/10** | `M1P6Z4` in the 3 misses |
| distant | baseline (newest first) | **10/10** | designated, 10/10 |
| distant | challenge (newest second, index 310) | **2/10** | `M1P6Z4` in the 8 misses |

Adjacent: 0 improved / 3 worsened, exact two-sided McNemar p = 0.25.
Distant: 0 improved / 8 worsened, exact two-sided McNemar p = 0.0078125.

All 40 rows finished normally (`finish_reason=stop`, 16–17 completion tokens),
carried `matched_input_tokens = condition_input_tokens = usage_prompt_tokens =
7271` with zero padding and zero usage mismatches, and contained no
`reasoning_content`. Misses are unambiguous: every failure emitted `M1P6Z4`, the
older chunk, never the newest code.

Latency (client end-to-end, n=10 per condition, batch 0 / batch 1): adjacent p50
9,885.6 / 9,890.8 ms, p95 12,973.2 / 13,007.3 ms; distant p50 9,882.0 / 9,881.9
ms, p95 12,954.1 / 12,941.8 ms. Peak sampled VRAM 1,702.1 MiB in all four leases.

## Interpretation

Three points, same content, same token budget:

| Duplicates | Placement | Challenge exact |
|---:|---|---:|
| 2 | adjacent (170, 171) | 7/10 |
| 2 | far apart (170, 310) | 2/10 |
| 9 | spread (170, 205–310) | 0/10 |

So the failure is not an artifact of having nine candidates. **Two** duplicate
versions are enough to break the answer most of the time when they are separated,
and even when they are adjacent the model still fails 3 times out of 10. Accuracy
degrades with both duplicate count and distance.

The adjacency result is the more interesting one for deployment. When the two
versions sit next to each other the model gets it right 70% of the time, which is
consistent with it occasionally reading the pair as a unit and comparing the
dates. When the same two chunks are 140 filler rows apart it drops to 20%, i.e.
essentially first-match behaviour. Nothing in the prompt changed.

Deployment consequence: "top-k retrieval returned the current version somewhere
in the context" is not sufficient. The practical fixes remain context-side —
de-duplicate to a single version per record, or place the authoritative version
first — and they matter even for k=2. Merging adjacent chunks of the same record
during indexing (so versions cannot both survive) is a cheap way to remove the
failure mode entirely.

Observation, not a general claim: ten synthetic targets, one chunk template, two
placements, temperature 0 with a single sample per condition, thinking disabled,
and a fixed 7,271-token context.

## Reproducibility and safety

Raw artifacts contain full prompts, generation requests/responses, input-token
count requests/responses, padding provenance, usage counts, campaign metadata,
logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-adjacent-pair-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-adjacent-pair-conflict-b1/`
- `results/campaigns/gpu-lab-longctx-needle-distant-pair-conflict-b0/`
- `results/campaigns/gpu-lab-longctx-needle-distant-pair-conflict-b1/`

All four campaigns recorded `status=measured`, exit code 0, `max_gen_toks=512`,
`constrain=false`, q8_0 K/V, and `needle_batch` 0 and 1; each suite's two batches
were disjoint five-target halves covering all ten targets. They ran as gpu-lab
generations 327, 328, 329 and 330 under the existing 400-second per-lease policy;
all terminal attempts were `supervisor_stopped/restored`. After each lease the
runner restored the original experiment config (SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`) and verified
real production inference (`recovered: OK`, `/health` HTTP 200,
`active_requests=0`).

## Limits

Ten fixed synthetic targets, one deterministic sample per condition, one model
and server configuration. The adjacent and distant suites differ only in filler
index, but that index is not the only difference in attention terms: the distant
challenge also places the older chunk at the 50% mark, which earlier suites
(`needle_position_conflict`) showed is itself a strong attractor. So this design
cannot separate "adjacent is easier" from "the 50% index is stickier", though both
readings support the same deployment advice. Sample sizes are small: 7/10 versus
2/10 is a real difference in these runs, but the adjacent arm's 3 misses are too
few for a tight rate estimate.

Untested and worth doing next: three duplicates (adjacent pair plus one distant)
to see whether the intermediate count behaves like 2 or like 9; a variant where
the two adjacent chunks are merged into one chunk carrying both versions, which is
what a real chunker would produce; and the same panel with a larger model, to
check whether the adjacency effect is a capacity limit.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

# Matched-length distractor retrieval at long context

## Question and design

At a fixed rendered prompt length, do plausible competing record/code facts reduce
exact retrieval of a target code compared with the existing repeated-filler
baseline?

Ten fixed target records (`K01`–`K10`) were each run in both conditions. The target
record stayed at the 50% filler-row position. The baseline used the existing
340-row filler prompt; the distractor condition replaced eight later filler rows
with unique decoy record/code facts. The query and instruction were unchanged.
Condition order alternated within target pairs, and the targets were split across
two five-pair leases to fit the existing lease deadline.

Before generation, both full chat-completion payloads were measured through
llama.cpp's `/v1/chat/completions/input_tokens` endpoint, which renders the same
chat template as completion. Baseline prompts were 7,181 tokens. Distractor
prompts were 7,141 tokens before padding; 40 neutral `x` tokens were appended
before the final query to reach 7,181. Every completion's `usage.prompt_tokens`
was checked against that count. Generation settings were identical: Qwen3-1.7B
Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0, cap 512,
one client, no response constraint, seed 42. Exact target-code match is the
primary outcome.

## Results

| Condition | Exact retrieval | Empty | Finish reason | Input-token mismatches |
|---|---:|---:|---|---:|
| Filler baseline | **10/10** | 0 | 10 stop | 0 |
| Eight decoys | **10/10** | 0 | 10 stop | 0 |

All ten pairs had equal 7,181-token inputs and matching `usage.prompt_tokens`; all
returned the expected target code. Paired discordance was 0 improved / 0 worsened;
the exact two-sided McNemar result is p=1.0. This describes the observed fixed
panel; it is not evidence of equivalence. With n=10, even 10/10 successes have a
Wilson 95% lower bound of about 0.72.

Both leases sampled peak VRAM at 1,702.1 MiB. Each lease made ten completion
requests (five pairs): batch 0 p50/p95 latency 13,047/16,443 ms; batch 1
14,338/18,263 ms. Pooled condition medians were 13,047 ms baseline and 13,604 ms
distractor, with median paired distractor-minus-baseline latency +451 ms. Timing
is descriptive only; small n, request order, prefix-cache reuse, and session
effects limit interpretation.

## Reproducibility and safety

The batch artifacts contain full prompts, generation requests/responses, input
token-count endpoint requests/responses, token-padding provenance, usage counts,
campaign metadata, logs and 1 Hz VRAM samples:

- `results/campaigns/gpu-lab-longctx-needle-distractor-b0/`
- `results/campaigns/gpu-lab-longctx-needle-distractor-b1/`

Both campaigns recorded `status=measured`, exit code 0, and distinct run keys.
The five target IDs in each batch were disjoint and together covered all ten.
They ran as gpu-lab generations 286 and 287 under the existing 400-second
per-lease policy; both terminal attempts were `supervisor_stopped/restored`.
After each lease, production was checked with a real completion and
`active_requests=0`; the final check reported `lease production 287 active 0;
recovered: OK`, and `/health` returned HTTP 200. The original experiment config
was restored with SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`.

## Interpretation and limits

No degradation was observed from these eight decoys in this synthetic task, but
both conditions were at ceiling. The sample is ten fixed synthetic targets,
not natural-language documents or a representative RAG workload; the decoys were
placed after the target and token-length equality was obtained with neutral `x`
padding. This cannot establish equivalence, general positional robustness, or
robustness to semantically similar/contradictory documents. A useful next test
needs a harder retrieval set that avoids the current ceiling while retaining
paired, equal-token prompts.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

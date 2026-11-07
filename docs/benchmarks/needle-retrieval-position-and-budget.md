# Exact retrieval by context position and response budget

## Question and design

Can Qwen3-1.7B retrieve a synthetic exact code from a roughly 7k-token prompt,
and do empty responses indicate failed retrieval or an exhausted output budget?

Each prompt contains 340 repeated filler rows and one unique code for a requested
record, placed at 10%, 50%, or 90% of the rows. Ten fixed record/code pairs form
the case panel. At 50% position, cap 64 and cap 512 were run on the same ten
prompts; only the generation cap changed. Each position then had one cap-512 run
of ten cases. Conditions used temperature 0, one client, no constrained decoding,
Qwen3-1.7B Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
b12024, ctx 8192, and q8_0 K/V cache.

The primary outcome is exact code match (`exact_match` from the existing
`LongContextEvaluator`). All requests, complete responses, usage and finish
reasons are retained. Prompt token counts are server-reported usage rather than
estimates from filler length.

## Results

| Needle position | Generation cap | Exact / 10 | Empty | Finish reasons | Prompt tokens / item | p50 / p95 latency (ms) | Peak VRAM (MiB) |
|---|---:|---:|---|---|---:|---:|---:|
| 50% | 64 | 0/10 | 10 | 10 `length` at cap | 7,181 | 11,047 / 14,132 | 1,702.1 |
| 50% | 512 | 10/10 | 0 | 10 `stop` | 7,181 | 13,843 / 18,156 | 1,702.1 |
| 10% | 512 | 10/10 | 0 | 10 `stop` | 7,181 | 17,781 / 18,452 | 1,702.1 |
| 90% | 512 | 10/10 | 0 | 10 `stop` | 7,181 | 8,752 / 16,863 | 1,702.1 |

For the paired 50%-position prompts, all ten cap-64 cases failed and all ten
cap-512 cases passed exact matching; there were 10 improvements and zero
regressions (two-sided exact McNemar `p = 0.001953`). At cap 64, every response
was empty, used exactly 64 completion tokens and ended with `finish_reason=length`.
At cap 512, all ten returned the exact code and ended with `stop`; completion
lengths were 121–222 tokens. This is direct evidence that the output budget was
insufficient for these ten responses, rather than evidence that retrieval failed
in those same prompts.

At cap 512, all 30 cases across the three positions were exact matches, with no
empty responses or generation-cap hits. This does not establish position
invariance: positions were run in a fixed, non-counterbalanced session order,
with one batch per position. The ten records are a fixed synthetic panel, not a
random sample of real RAG questions. For 10/10 successes, a 95% Wilson interval
has a lower bound of about 0.72.

## Limitations

- “Depth” is the position among repeated character rows, not a tokenizer-derived
  token offset. All prompts reported 7,181 input tokens, but this experiment does
  not identify exact token-index placement effects.
- The cap-64 versus cap-512 comparison is paired and changes only `max_tokens`,
  but is limited to these ten fixed prompts, this model/runtime, and this output
  format.
- The 10%, 50%, and 90% batches ran sequentially, not randomized or interleaved.
  Their latency differences are descriptive; session/order and cache effects are
  plausible, so no latency-position effect is claimed.
- A separate 30-prompt cap-64 attempt exceeded the existing 400-second gpu-lab
  deadline. The controller cleaned up and restored the system, but wrote no
  response-level results; it is excluded. Partial logs and an incomplete marker
  are retained under `results/campaigns/gpu-lab-longctx-needle-pos-seed42/`.

## Reproduction and artifacts

Campaign metadata, raw responses, logs and VRAM samples are preserved under:

- `results/campaigns/gpu-lab-longctx-needle-depth50-seed42/` (cap 64)
- `results/campaigns/gpu-lab-longctx-needle-depth50-cap512-seed42/`
- `results/campaigns/gpu-lab-longctx-needle-depth10-cap512-seed42/`
- `results/campaigns/gpu-lab-longctx-needle-depth90-cap512-seed42/`

The runs used the existing 400-second gpu-lab lease deadline. Every completed
lease reached terminal restored state; afterward production had zero active
requests and passed a real inference health check. No production/controller
configuration was changed. The original experiment env file was restored
byte-for-byte.

Methodological design and claim calibration were informed by Kassis, T., Agarwal,
V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A
Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

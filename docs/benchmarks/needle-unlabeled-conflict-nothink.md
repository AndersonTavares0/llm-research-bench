# Disabling thinking rescues same-record conflict retrieval

## Question and design

The previous study (`needle-unlabeled-conflict.md`) found that Qwen3-1.7B failed
7/10 unlabeled same-record conflicts at a 512-token generation cap. Every miss was
not an empty server response: `finish_reason` was `length`, `content` was empty, and
`message.reasoning_content` held 1,903–4,149 characters of the model arguing with
itself about which of the nine same-record codes was current. Raising the cap to
1,000 (the maximum possible under ctx 8192 with 7,181-token prompts) only rescued
3 of those 7.

That makes a sharp, cheap follow-up: if the failures are deliberation-budget
artifacts, disabling thinking mode at the *same* cap should remove them. This is
the same suite, same ten target records, same prompts, same server, same
`max_tokens=512` — the only change is `chat_template_kwargs:
{"enable_thinking": false}` on the request.

Design is unchanged from the parent study: 340 filler rows, the target
`Record {id}: the exact field code is {value}.` at index 170 (50%), and a challenge
arm that replaces the eight rows at indices 205–310 with *the same record ID*
carrying eight different codes. No `ACTIVE`/`ARCHIVED`/`superseded` wording exists
in either arm, so position and recency are the only available cues.

Both full chat-completion payloads were measured through llama.cpp's
`/v1/chat/completions/input_tokens` endpoint and padded to a common rendered
length before generation. Ten target records were split across two five-pair
leases. Settings: Qwen3-1.7B Q4_K_M (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
0.8.0-dev build12024 (`ddf48f85c`), ctx8192, q8_0 K/V, temperature 0, one client,
no response constraint, seed 42, `max_gen_toks=512`.

## Manipulation check

The switch reached the server and took effect on all 20 generation rows:

| Check | Result |
|---|---|
| `chat_template_kwargs` in stored request | `{'enable_thinking': False}` on 20/20 |
| Non-empty `reasoning_content` | 0/20 |
| `finish_reason` | `stop` on 20/20 |
| Challenge completion tokens | 16–18 (baseline 16–20) |
| Matched rendered tokens | 7,185 both arms, 10/10 pairs |
| `usage_prompt_tokens == matched_input_tokens` | 20/20 |

Thinking-disabled requests render 7,185 tokens instead of 7,181 because the chat
template emits an empty think block. Token parity is preserved *within* each pair;
the 4-token difference between the thinking and no-thinking runs is template
scaffolding, and is the one confound in the cross-run comparison below.

## Results

Same ten cases, same cap of 512, thinking on versus off:

| Arm | Baseline exact | Challenge exact | Challenge `length` | Challenge empty |
|---|---:|---:|---:|---:|
| Thinking on (cap 512) | 10/10 | **3/10** | 7 | 7 |
| Thinking off (cap 512) | 10/10 | **10/10** | 0 | 0 |

Per case, challenge arm:

| Case | Expected | Thinking on | Thinking off |
|---|---|---|---|
| K01 | Q7M4K2 | correct (162 tok) | correct (16 tok) |
| K02 | P9V3D6 | correct (484 tok) | correct (18 tok) |
| K03 | R2C8W5 | truncated at 512 | correct (18 tok) |
| K04 | H6N1X4 | truncated at 512 | correct (18 tok) |
| K05 | B3T9L7 | truncated at 512 | correct (18 tok) |
| K06 | M5F2Z8 | truncated at 512 | correct (18 tok) |
| K07 | C8J4A1 | correct (323 tok) | correct (18 tok) |
| K08 | W1G7P3 | truncated at 512 | correct (16 tok) |
| K09 | D4Y6S2 | truncated at 512 | correct (16 tok) |
| K10 | X2L5N9 | truncated at 512 | correct (18 tok) |

Paired thinking-on → thinking-off: 7 improved, 0 worsened, exact two-sided McNemar
p=0.015625. The baseline arm was unaffected (10/10 either way), which is the
expected pattern if the change acts on conflict deliberation rather than on
retrieval generally.

Latency (client end-to-end, ten completions per condition):

| Arm | Baseline p50 | Challenge p50 | Challenge max |
|---|---:|---:|---:|
| Thinking on | 13,117 ms | 23,097 ms | 24,829 ms |
| Thinking off | 9,589 ms | 7,981 ms | 9,647 ms |

Disabling thinking cut challenge latency roughly 2.9x and removed the long tail,
because no request spent hundreds of tokens reasoning before answering.

## Interpretation

Within this synthetic suite, the earlier "retrieval failure" was a *generation
budget* failure. Given the same context and the same 512-token allowance, thinking
mode spent the entire allowance deliberating an ambiguity that had no textual
resolution and never emitted an answer; with thinking disabled the model answered
directly and correctly in 16–18 tokens on all ten cases.

Two observations sharpen this beyond "more budget helps":

- At cap 1,000 with thinking on, K04 was answered **wrong** — the model chose
  `M1P6Z4`, the *last*-listed of the nine same-ID codes, reasoning "the exact code
  for K04 is the last one listed". With thinking off, K04 answered the 50% row
  correctly. So the no-think path is not simply picking by recency.
- Thinking off produced zero decoy codes across all ten cases, while thinking on
  produced one decoy answer once it had enough budget to reach a conclusion.

## Limits

- The no-thinking arm is again at ceiling (10/10), so this run shows that the
  observed failures disappear; it does not establish general conflict-resolution
  skill. With n=10, 10/10 has a Wilson 95% lower bound of about 0.72.
- The cross-run comparison changes the rendered prompt length by 4 tokens
  (7,181 → 7,185) because the template differs. Prompt *content* is identical and
  each run is internally token-matched, but this is not a strictly length-matched
  A/B.
- Greedy decoding with one run per arm: identical completion-token counts for
  K01/K02/K07 in the thinking runs at both caps showed the runs are not independent
  samples, and the same caution applies here.
- The task is synthetic and fixed: nine same-ID codes separated by 340 filler rows
  of repeated prose. Natural documents, contradictory prose, and multi-hop
  questions remain untested.
- Disabling thinking is not a free win in general — it removes deliberation that
  other tasks may need. This experiment only shows that for a *conflict the context
  cannot resolve*, deliberation burns the budget without improving the answer.

## Reproducibility and safety

Raw artifacts (full prompts, requests with `chat_template_kwargs`, responses
including `reasoning_content`, input-token counts, padding provenance, usage,
campaign metadata, logs, 1 Hz VRAM):

- `results/campaigns/gpu-lab-longctx-needle-unlabeled-conflict-nothink-b0/`
- `results/campaigns/gpu-lab-longctx-needle-unlabeled-conflict-nothink-b1/`

Both campaigns recorded `status=measured`, exit code 0. They ran as gpu-lab
generations 298 and 299 under the existing 400-second per-lease policy; both
terminal attempts were `supervisor_stopped/restored`. After each lease, production
was checked with a real completion: `lease production 298 active 0; recovered: OK`
and `lease production 299 active 0; recovered: OK`, with `/health` HTTP 200. The
original experiment config was restored with SHA-256
`b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`.

The no-think request is fail-closed in code: `think=False` raises unless the suite
is one of the paired needle suites, so the switch cannot silently leak into other
probes.

The controlled-design and claim-calibration approach was informed by Kassis, T.,
Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent
Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

# Generation cap and constrained-output failures at ~6.8k context

## Question and paired design

Does raising the generation-token cap from 256 to 512 rescue the six failures in
the fixed 30-case structured-output suite at long context? The arms use the same
Qwen3-1.7B Q4_K_M file (SHA-256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`), llama.cpp
b12024, ctx 8192, q8_0 K/V, 6,800 filler setting, strict prompt, JSON-schema
`response_format`, temperature 0, seed 42, and one client. Only `max_tokens`
changes. The 256 arm is the existing 30-case campaign; the new 512 arm ran all
30 cases, matched by the final task line. This is a paired fixed benchmark suite,
not a random sample of all prompts or models.

## Results

| Cap | Schema-valid | Empty | Invalid/truncated JSON | Finish reason | p50 / p95 |
|---|---:|---:|---:|---|---:|
| 256 | 24/30 | 4 | 2 | 24 stop, 6 length | 6,090 / 8,179 ms |
| 512 | 30/30 | 0 | 0 | 30 stop | 6,105 / 9,939 ms |

All six failures at 256 used exactly 256 completion tokens and had
`finish_reason=length`; prompt usage was 7,235–7,241 tokens. Each became valid at
512, stopped normally, and used 261–321 completion tokens. No case regressed.
Exact two-sided McNemar test: 6 improved / 0 worsened, **p = 0.03125**. This is a
nominal exploratory paired test on a pre-existing fixed suite; repeated prompts
are not independent replication, and the p-value does not establish generality.

Peak sampled VRAM was 1,702.1 MiB in both runs. The higher cap did not increase
the preallocated KV footprint. The observed p95 latency increased by about 1.8 s;
per-case latency can be affected by the extra generated tokens and response mix.

## Interpretation

For these six long-context failures, the generation cap was insufficient: the
server explicitly reported length termination at the exact cap, and doubling it
allowed every response to complete. This provides direct evidence for a token-
budget explanation of these cases. It does **not** establish that all empty or
truncated outputs are cap failures, identify a universal grammar/EOS mechanism,
or show that a larger cap improves general quality. Earlier 128-token mechanism
probes similarly showed cap exhaustion for two short prompts, but remain separate
from this long-context result.

## Reproduction and provenance

Raw requests, complete responses (including reasoning, usage and finish reason),
campaign metadata, logs and VRAM samples are in:

- `results/campaigns/gpu-lab-longctx-audit-reason-256/`
- `results/campaigns/gpu-lab-longctx-audit-reason-512-full30/`

The 512 campaign metadata records exit code 0, limit 30, seed 42, context fill
6,800, strict prompting and the model/runtime/server configuration. It completed
under the existing gpu-lab lease policy; controller terminal state was restored,
and production health plus a real completion were verified afterward.

The follow-up `json_schema` versus generic `json_object` comparison, including
reversed-order repeats and a review of the transient boundary refusals, is
documented in `constraint-format-7k.md`.

Methodological design and claim calibration were informed by Kassis, T., Agarwal,
V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A
Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065.
https://doi.org/10.48550/arXiv.2609.00065

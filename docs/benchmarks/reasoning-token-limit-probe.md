# Reasoning tokens and empty responses: exploratory probe

Three short, intentionally contradictory instructions were tested with the same
Qwen3-1.7B Q4_K_M model and server configuration, crossing JSON-schema response
format (on/off) with the completion limit (128/256). These are matched prompts,
not independent samples; the four leases were not randomized. The raw requests,
complete responses, usage, finish reasons, server logs and metadata are under
`results/campaigns/gpu-lab-mechanism-audit-{con128,free128,con256,free256}/`.

| Response format | Limit | WORLD: finish / tokens | HELLO: finish / tokens | 7: finish / tokens |
|---|---:|---|---|---|
| schema | 128 | stop / 125 | length / 128 | length / 128 |
| unconstrained | 128 | stop / 116 | length / 128 | length / 128 |
| schema | 256 | stop / 125 | stop / 151 | stop / 215 |
| unconstrained | 256 | stop / 116 | stop / 137 | stop / 203 |

Both HELLO and 7 responses at 128 had empty visible content and nonempty
`reasoning_content`. At 256 both produced visible answers in both arms. The
schema arm produced JSON, while the unconstrained arm returned plain text.
Thus a token limit consumed alongside hidden reasoning is supported for these
particular empty outputs; increasing the limit resolved them here. It does not
establish EOS behavior, grammar enforcement in general, or the cause of the
older long-context failures, whose finish reasons and usage were not recorded.
Contradictory prompts and three cases limit generalization.

The controller reported cleanup and production restoration after each lease;
production answered a real request at generation 264. One intervening attempt
was refused by the boundary check because of a foreign process; no bypass was
used, and a later normal attempt succeeded after the process had exited.

## Methodological guidance

The experimental-design and scientific-critical-thinking skills informed the
matched comparison and treatment of dependent repeats: Kassis, T., Agarwal, V.,
He, Y., Patel, D., & Brueckner, A. M. (2026), *Scientific Agent Skills: A Library
of Procedural Knowledge for Research Agents*, https://doi.org/10.48550/arXiv.2609.00065.

## Follow-up at ~7k context (30-case structured suite)

A subsequent constrained run used the same Qwen3-1.7B Q4_K_M model, q8_0 KV,
ctx 8192, 6,800 filler setting, strict prompt, JSON schema, temperature 0, and
30-case suite, with `max_tokens=256`. All six invalid cases ended with
`finish_reason=length` at exactly 256 completion tokens; four had empty visible
content and two had partial JSON. Their `reasoning_content` ranged from 1,053 to
1,088 characters. Recorded prompt usage was 7,235–7,241 tokens, so prompt plus
completion remained within the 8,192-token context.

| Outcome among 30 | Count |
|---|---:|
| Valid JSON/schema | 24 |
| Empty visible content; length stop at 256 | 4 |
| Partial/invalid JSON; length stop at 256 | 2 |
| Other failures | 0 |

This directly establishes that the six observed failures in this run exhausted
the configured generation budget; it does **not** show that every long-context
failure has that cause, nor that a larger budget fixes all of them. The prior
short-prompt 128→256 mechanism probe independently showed those three particular
empty responses become nonempty with the larger budget. A paired 7k 256→higher-cap
run remains unperformed, so a long-context mitigation effect is still unmeasured.

Artifacts, including full prompt/response objects and usage/finish metadata:
`results/campaigns/gpu-lab-longctx-audit-reason-256/`. Run summary records a
measured campaign and 30-case structured group; production recovery was verified
at generation 265 (`active_requests=0`). The remote run configuration was
`longctx-config-next.env`; `run-longctx.sh` reads it after the legacy config so
these one-off settings do not overwrite the existing config.

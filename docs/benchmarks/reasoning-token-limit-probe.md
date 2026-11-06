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

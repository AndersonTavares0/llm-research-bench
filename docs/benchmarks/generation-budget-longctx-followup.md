# Higher generation cap at ~6.8k context: paired subset

## Question and design

Hypothesis: some constrained-output failures at 6.8k context occur because Qwen3's
reasoning consumes the generation budget before it emits the requested JSON. Compare
a 256-token cap with 512 on the same model, prompt subset, context fill, schema,
prompt wording, temperature, KV precision, and context size. The changed variable
is only `max_tokens` (256 → 512). The lower-cap arm is drawn from the earlier
30-case run; the higher-cap arm is a new 12-case lease using the campaign's fixed
first 12 cases. This is a paired, exploratory subset, not a randomized sample.

- Model: Qwen3-1.7B Q4_K_M, SHA-256
  `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`
- Runtime: llama.cpp b12024; ctx 8192; q8_0 K/V; temperature 0; strict prompt;
  constrained JSON schema; 6,800 filler setting; one client.
- The 256-token arm had 30 cases; the 512-token arm covered the matching fixed
  12-case subset. Prompt identity was matched by the final task line.

## Paired results

| Outcome | 256 cap, same 12 cases | 512 cap |
|---|---:|---:|
| Schema-valid outputs | 10/12 | 12/12 |
| Empty outputs | 1 | 0 |
| Invalid/truncated JSON | 1 | 0 |
| Peak sampled VRAM | 1,702.1 MiB | 1,702.1 MiB |
| Latency p50 / p95 | from 30-case arm: 6,090 / 8,179 ms | 6,513 / 14,685 ms |

Both discordant cases improved (0 worsened): Grace Hopper was truncated at 256 and
completed at 309 tokens; Tokyo was truncated at 256 and completed at 261 tokens.
Both 512-token outputs ended with `finish_reason=stop` and passed schema validation.
The other ten cases remained valid; their completion token counts and returned
content matched between runs. Exact two-sided McNemar p = 0.50 (2 discordant pairs),
so this small paired sample is descriptive, not confirmatory.

In the full 30-case 256 run, six failures all ended at `finish_reason=length` and
exactly 256 completion tokens. In this selected 12-case subset, both failures were
rescued by the higher cap. Together with the short-prompt cap probe, this supports
generation-budget exhaustion as a cause for these specific truncations. It does
not establish a universal mitigation effect, nor does `finish_reason=stop` alone
identify the internal EOS/grammar mechanism.

## Safety and provenance

The first attempted lease was refused at bind because the controller detected a
foreign `bash` PID in the generation cgroup; the controller restored production.
No safety check was bypassed. After the PID disappeared, a normal launcher retry
bound successfully at generation 267. The campaign metadata records exit code 0
and the production verification returned `lease production 267 active 0; recovered: OK`.

Raw requests, full responses, usage, finish reasons, `meta.json`, and sampled VRAM:
- `results/campaigns/gpu-lab-longctx-audit-reason-256/`
- `results/campaigns/gpu-lab-longctx-audit-reason-512-seed42-n12/`

The 256 arm's 1-Hz VRAM trace was recovered alongside the artifacts; the 512 arm
used 92 samples. Both peaked at 1,702.1 MiB. The result indicates that 512 fits
comfortably on the 4-GiB card for this fixed context and workload.

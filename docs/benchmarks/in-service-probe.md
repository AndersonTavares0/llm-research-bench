# In-service latency probe: GTX 1050 Ti, 2026-11-05

This is **not a campaign**. It measures the production llama-server as deployed,
without a lab lease, to answer three serving questions the offline campaigns
cannot: how latency scales with prompt length, whether prefix caching actually
helps under the production settings, and what happens to latency when two
clients share the single slot.

Artifact: [`results/in-service/2026-11-05-qwen3.5-4b-probe.json`](../../results/in-service/2026-11-05-qwen3.5-4b-probe.json).
Probe: `tools/homelab/in-service-probe.py` (public chat endpoint only, 18 requests).

## Configuration actually used

| Item | Value |
|---|---|
| GPU | GTX 1050 Ti, 4096 MiB |
| Service | production gateway on port 18081 → llama-server, `qwen3.5:4B` |
| Server args | ctx 32768, `--parallel 1`, KV q8_0, `--cache-ram 0`, draft-MTP |
| Decoding | temperature 0, `max_tokens` 32, no streaming |
| Volume | 4 lengths × 3 reps, 3 cache repeats, 3 concurrency rounds |

## Finding 1 — end-to-end latency is linear in prompt length

| Prompt tokens | Wall p50 | Server prefill | Decode |
|---:|---:|---:|---:|
| 107 | 1,122 ms | 194 tok/s | 22.9 tok/s |
| 443 | 2,223 ms | 293 tok/s | 24.3 tok/s |
| 1,283 | 4,710 ms | 308 tok/s | 24.2 tok/s |
| 2,543 | 9,116 ms | 300 tok/s | 24.9 tok/s |

The slope is ≈ 3.5 ms per prompt token at steady state (prefill ~300 tok/s on this
4B model with MTP). Decode is flat at ~24 tok/s, so for long prompts time-to-first
-token dominates and output length is a second-order cost until roughly 4k tokens.

Note the difference from the Qwen3-1.7B campaign (848 tok/s prefill, 48 tok/s
decode): a 4B model at 4 GiB is roughly 2.4× slower to prefill and 2× slower to
decode. That is a model-size effect, not a regression.

## Finding 2 — prefix caching is already effective in production

The same 40-repetition prompt sent three times:

| Request | `cache_n` | Server prompt time |
|---|---:|---:|
| 1 | 0 | 2,854 ms |
| 2 | 859 | 116 ms |
| 3 | 859 | 116 ms |

A cache hit cut prefill time by **24.6×** (2,854 → 116 ms) even though the host
prompt cache is disabled (`--cache-ram 0`): the reuse happens in the VRAM KV
cache for an identical prefix. This explains why the earlier OOM fix does not
throw away the main caching benefit — it only removes the unbounded host copy.

## Finding 3 — with one slot, a second client doubles tail latency

| Round | Client A wall | Client B wall |
|---|---:|---:|
| 1 | 9,387 ms | 4,005 ms |
| 2 | 4,014 ms | 8,021 ms |
| 3 | 4,006 ms | 7,934 ms |

Two ~600-token requests issued together serialize on the single slot: one client
gets the normal ~4 s, the other waits ~8–9.4 s. Aggregate throughput is unchanged;
the cost is entirely queueing. Concurrency work on this card therefore needs
`--parallel` slots or a scheduler; adding clients alone only moves latency into
the tail.

## Limitations

- The model is the production Qwen3.5-4B (Q4_K_M + MTP), not the campaign
  Qwen3-1.7B; numbers are not interchangeable.
- `--parallel 1`, ctx 32768 and draft-MTP are production settings, not controlled
  experiment factors.
- n=3 per cell; no confidence intervals are claimed, only medians of three runs.
- The service may have served other clients during the probe.
- No power, clock or temperature telemetry, and no VRAM sampling during the run.
- Requests are small in volume and sequential within each block.

## What this changes for the plan

- H3 (prompt-cache policy) is partly answered: VRAM prefix caching already gives
  ~25× prefill savings, so the remaining question is the host cache's benefit for
  *non-identical* prefixes, not whether caching matters.
- H4 (concurrency) gains a concrete prior: at one slot, a second client roughly
  doubles the slower client's latency. The sweep should compare 1/2/4 slots with
  a fixed two-client arrival pattern, not just aggregate tok/s.
- H1 (context/KV) remains open and still needs the lease: this probe shows
  latency, not the memory ceiling.

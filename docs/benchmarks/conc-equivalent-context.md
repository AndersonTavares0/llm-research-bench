# Concurrency with equivalent per-slot context (GTX 1050 Ti)

Follow-up to `h4-concurrency-repeats.md`, which compared 1 vs 4 slots at a fixed
total ctx 8192 — i.e. 8192 tokens of context per request at 1 slot but only 2048
at 4. This run removes that confound: total context scales with slots so every
configuration gets **2048 tokens per slot**.

| Slots | `--ctx-size` | Context per slot |
|---:|---:|---:|
| 1 | 2048 | 2048 |
| 2 | 4096 | 2048 |
| 4 | 8192 | 2048 |

Artifacts: `results/campaigns/gpu-lab-conc-equiv-*/`.

## Method

Qwen3-1.7B Q4_K_M, q8_0 KV, `cache_ram 0`, `enable_thinking=false`, 6 rounds of
~600-token prompts, temperature 0, two client loads (2 and 4 simultaneous
requests), one lease per cell (≤2 min). llama-bench was disabled so the lease
stays inside the interruption budget; that also means no VRAM sampling in this
run.

## Results

| Slots | Clients | Aggregate req/s | p50 | p95 | Slowest |
|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 0.611 | 2,486 ms | 3,297 ms | 3,337 ms |
| 1 | 4 | 0.613 | 4,087 ms | 6,532 ms | 6,536 ms |
| 2 | 2 | 0.736 | 2,703 ms | 2,825 ms | 2,825 ms |
| 2 | 4 | 0.716 | 4,640 ms | 5,693 ms | 5,725 ms |
| 4 | 2 | 0.737 | 2,703 ms | 2,823 ms | 2,824 ms |
| 4 | 2 (repeat) | 0.733 | 2,741 ms | 2,822 ms | 2,823 ms |
| 4 | 4 | 0.770 | 5,209 ms | 5,252 ms | 5,256 ms |

## Findings

1. **Throughput saturates at one slot per concurrent client.** With 2 clients,
   2 slots already reach 0.736 req/s and 4 slots add nothing (0.737, 0.733 on a
   repeat). Extra slots beyond the client count buy no throughput.
2. **Four clients need four slots.** At 1 slot, 4 clients do not increase
   throughput at all (0.613 vs 0.611) and double the median (4.09 s) and p95
   (6.53 s) — pure queueing. At 4 slots the same load reaches 0.770 req/s
   (+25.6% over 1 slot) with p50 5.21 s.
3. **Latency follows slots, not total context.** With 2 clients, p50 is 2.70 s at
   both 2 and 4 slots, i.e. the earlier "4 slots are slower" result was caused by
   the per-slot context difference, not by slot count.
4. **Repeatability of the aggregate metric is high**: the repeated 4-slot,
   2-client cell differs by 0.5% (0.737 vs 0.733), while its p50 varies by 1.4%.

## Limitations

- Most cells are a single run; only 4 slots / 2 clients was repeated. Treat
  between-run uncertainty as “≈1% on aggregate throughput”, not a full estimate.
- No VRAM sampling in this campaign (bench disabled); the earlier H1 data covers
  memory at these contexts.
- Two client loads only; the knee beyond 4 concurrent clients is unmeasured.
- 2048 tokens per slot is fixed; a longer-prompt workload would hit the per-slot
  limit at every configuration equally.

## Tooling notes

- `capability` now takes `--clients` and generates rounds from `--limit`
  (regression-tested).
- All cells initially failed with argparse `invalid choice: 'concurrency'`
  because the suite key had been removed while making the rounds dynamic; the key
  is retained for the choice list and a test pins it.
- One repeat lease was refused during the drain window (expected) and is recorded
  as a missing cell rather than retried indefinitely.

## Repeats and VRAM (follow-up run)

Three key cells were repeated with 1 Hz GPU-memory sampling inside the lease
(`capability --vram-csv`), staying under the 2-minute interruption cap.

| Config | Runs (req/s) | Mean ± SD | p50 runs | Peak VRAM |
|---|---|---:|---|---:|
| 1 slot, 2 clients | 0.611, 0.610 | 0.6105 ± 0.0007 | 2,486 / 2,515 ms | 1,340.1 MiB |
| 2 slots, 2 clients | 0.736, 0.737 | 0.7365 ± 0.0007 | 2,703 / 2,701 ms | 1,458.1 MiB |
| 4 slots, 2 clients | 0.737, 0.732, 0.733 | 0.7340 ± 0.0027 | 2,703 / 2,740 / 2,741 ms | 1,696.1 MiB |

- Between-run spread is **0.1–0.4%** on aggregate throughput, so the 2-slot
  saturation (+20.6% over 1 slot) is far outside the observed noise.
- Peak VRAM rises with total context exactly as the q8_0 KV slope predicts:
  1,340 → 1,458 MiB for +2048 tokens (≈59 KiB/token) and 1,458 → 1,696 MiB for
  another +4096 tokens (≈59.5 KiB/token), matching H1's 60.3 KiB/token.
- Three further repeat leases were refused during the drain window
  (`reservation refused`) and are recorded as missing cells rather than retried
  beyond the interruption budget.

New artifacts: `results/campaigns/gpu-lab-conc-equiv-{p1c2-r2,p2c2-r2,p4c2-r2}/`
including each cell's `vram.csv`.

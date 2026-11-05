# H4 repeats: concurrency gain with run-to-run variance (GTX 1050 Ti)

Six approved leases (generations 187–192), Qwen3-1.7B Q4_K_M, ctx 8192,
q8_0 KV, `cache_ram 0`, two simultaneous 600-token clients per round, 4 rounds
per cell, llama-bench 3 repetitions. Production was preempted per lease and
verified with a real completion after each release.

Artifacts: `results/sweeps/h4-par{1,4}-r{1,2,3}/` (rows, 1 Hz VRAM CSV,
campaign results).

## Per-lease measurements

| Slots | Repeat | Aggregate req/s | Slowest request | Request p50 | Peak VRAM |
|---:|---:|---:|---:|---:|---:|
| 1 | r1 | 0.611 | 3,283.9 ms | 2,460.0 ms | 1,702.1 MiB |
| 1 | r2 | 0.612 | 3,272.3 ms | 2,453.1 ms | 1,702.1 MiB |
| 1 | r3 | 0.612 | 3,276.8 ms | 2,456.9 ms | 1,702.1 MiB |
| 4 | r1 | 0.737 | 2,832.0 ms | 2,701.4 ms | 1,696.1 MiB |
| 4 | r2 | 0.728 | 2,831.2 ms | 2,761.5 ms | 1,696.1 MiB |
| 4 | r3 | 0.744 | 2,831.4 ms | 2,652.1 ms | 1,696.1 MiB |

## Summary (mean ± SD, n=3 per configuration)

| Metric | 1 slot | 4 slots | Difference |
|---|---:|---:|---:|
| Aggregate req/s | 0.6117 ± 0.0006 | 0.7363 ± 0.0080 | +0.1246 req/s (+20.4%) |
| Slowest request | 3,277.7 ± 5.8 ms | 2,831.5 ± 0.4 ms | −446 ms (−13.6%) |
| Request p50 | 2,456.7 ± 3.5 ms | 2,705.0 ± 54.8 ms | +248 ms (+10.1%) |
| Peak VRAM | 1,702.1 MiB | 1,696.1 MiB | −6 MiB |

Welch interval for the throughput gain at n=3+3 (t≈4.30, SE≈0.0047):
**+0.105 to +0.145 req/s**, i.e. roughly +17% to +24%. This is an interval
from three repetitions per arm, not a significance claim; the t approximation
with df≈2 is itself fragile.

## Interpretation

- Extra slots raise aggregate throughput ~20% and cut the worst-case request by
  ~14%, because the two clients overlap instead of serialising.
- Per-request median rises ~10%: with four slots both requests share the GPU
  from the start, while one slot serves one request at ~2.45 s and queues the
  other to ~3.28 s. The throughput/latency knee is real and small.
- VRAM is unchanged (within 6 MiB): at ctx 8192 the four slots partition the
  same KV budget, so slots trade per-slot context, not memory.

**Per-slot context caveat:** with `--ctx-size 8192`, 1 slot gives 8192 tokens of
context per request while 4 slots give 2048 each. The workload (600-token
prompts) fits both, so the comparison is workload-comparable but *not*
context-equivalent: the 4-slot configuration could not serve a prompt longer
than ~2048 tokens.

## Method lessons recorded

- Three payloads failed before measurement because `--campaign-suffix -r1` was
  parsed as an option (fixed, commit `4d53fd3`).
- Two leases were refused with `drain_failed` when a verification completion ran
  seconds before the next acquisition; the harness now waits ~45–60 s of quiet
  between leases. This is expected behaviour of the drain guard, not a defect.
- One recovery check hit `Connection refused` while the production model was
  still reloading; the follow-up check was healthy and `active_requests` returned
  to 0.

## Limitations

- n=3 per configuration, one GPU, one model/quantisation, one ctx.
- 4 slots at ctx 8192 is not context-equivalent to 1 slot at ctx 8192.
- Only two concurrent clients; the knee beyond four slots is unmeasured.
- No power/clock/temperature telemetry; no thermal control between leases.

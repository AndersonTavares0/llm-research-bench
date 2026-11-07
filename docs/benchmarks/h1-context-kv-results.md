# H1 results: context and KV-cache scaling on the GTX 1050 Ti

Measured on 2026-11-05 with the gpu-lab lease (generation 172), Qwen3-1.7B Q4_K_M
(SHA-256 `d2387ca2…c7b5`), llama.cpp b12024, ctx {2048, 4096, 8192} × KV {f16, q8_0}.

Artifacts: [`results/sweeps/ctxkv2/`](../../results/sweeps/ctxkv2/) — per-cell
`*-vram.csv`, `sweep_rows.json`, `sweep_analysis.json`, and the campaign runs.

## Method (and why it changed)

A llama-bench-only sweep cannot answer this question: llama-bench uses its own
context and never starts the campaign server, so six "ctx" cells produced six
identical memory values. The first attempt (generation 170, ~3.5 min of lease)
was therefore discarded; the lease was released and production restored.

The corrected spec (`configs/campaigns/gpu-lab-ctxkv-probe.yaml`) runs a
capability group per cell. That forces the server to start with the cell's
`--ctx-size` and `--cache-type-k/v`, and the sweep samples `nvidia-smi
memory.used` at 1 Hz for the whole cell. `llama-bench` is disabled
(`--no-bench`) so its separate process cannot set the memory floor. Peak values
below are the maximum sampled during the cell.

## GPU memory per cell

| ctx | KV f16 | KV q8_0 | q8_0 saving |
|---:|---:|---:|---:|
| 2048 | 1,432.1 MiB | 1,332.1 MiB | 100.0 MiB |
| 4096 | 1,658.1 MiB | 1,452.1 MiB | 206.0 MiB |
| 8192 | 2,110.1 MiB | 1,694.1 MiB | 416.0 MiB |

## Finding 1 — measured KV slope matches the analytical model

From 2048 → 8192 tokens (6144 tokens):

- f16: (2110.1 − 1432.1) / 6144 = **113.0 KiB/token**
- q8_0: (1694.1 − 1332.1) / 6144 = **60.3 KiB/token** (0.534 × f16)

The analytical prediction for Qwen3-1.7B is 112 KiB/token
(28 layers × 8 KV heads × 128 × 2 × 2 B), so the measurement agrees within 1%.
The fixed cost (weights, compute buffers, CUDA context) is
1432.1 − 2048 × 0.1104 = **≈1,206 MiB**; KV is the only part that scales with
context.

## Finding 2 — headroom at 8192 is comfortable; q8_0 buys ~2× context

At the largest measured cell (8192, f16) the card holds 2,110 MiB, leaving
~1.99 GiB free of 4,096 MiB. Extrapolating the measured slope from the 3,048 MiB
above the fixed cost:

- f16: ≈ 27.6k tokens
- q8_0: ≈ 51.7k tokens

These are extrapolations, not measurements: allocator granularity, compute
buffers and the sandbox's 3 GiB host-RAM limit are not modelled, and nothing
above 8192 was run.

## Finding 3 — latency did not move with context at small prompts

Structured-output probes (3 cases per cell) show p50 between 589 and 603 ms and
p95 between 606 and 627 ms across all six cells. At these prompt sizes the
request is dominated by fixed overhead, so this is a null result, not evidence
that context is free: the in-service probe already showed ~3.5 ms per prompt
token at larger lengths.

## Finding 4 — capability probes on Qwen3-1.7B (measured, not smoke-tested)

| Suite | Cases | Valid | Rate | 95% Wilson | p50 | p95 |
|---|---:|---:|---:|---|---:|---:|
| Structured output (JSON schema) | 10 | 10 | 1.00 | 0.722–1.000 | 497 ms | 619 ms |
| Tool calling (name + JSON args) | 5 | 5 | 1.00 | 0.566–1.000 | 611 ms | 772 ms |

Artifacts: `results/campaigns/gpu-lab-capability-probe-v1/…/{structured,tools}/`.
Both intervals include 1.0; with 5 and 10 cases the probe cannot resolve rates
below ~0.57 and ~0.72 respectively. These are functional checks, not capability
rankings.

## Limitations

- One lease per cell; no repeated leases, so between-run variance is unknown.
- Peak memory comes from a 1 Hz sampler, so sub-second spikes are invisible.
- No power, clock or temperature telemetry.
- The capability suites are small, synthetic and fixed (10 + 5 cases).
- Only Qwen3-1.7B Q4_K_M was measured; no Q8_0 or 3B model.

## Decisions

1. **q8_0 KV is the default for long-context work on this card**: it halves the
   KV slope (0.534×) with no measured latency change, and no quality check at
   n≥100 has been run yet — that is the next experiment, not a conclusion.
2. The 8192-ctx f16 configuration is safe on a 4 GiB card (~2.0 GiB headroom);
   the earlier 3 GiB sandbox OOM was host RAM (prompt cache), not VRAM.
3. Future sweeps must start the server per cell; bench-only cells answer a
   different question and should be labelled as such.

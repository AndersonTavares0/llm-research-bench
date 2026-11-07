# H2/H4 + KV-quality results (GTX 1050 Ti, 2026-11-05)

Three measurements from one lease series (generations 173–177), Qwen3-1.7B
Q4_K_M (`d2387ca2…`) and Llama-3.2-3B-Instruct Q4_K_M
(`bartowski` rev `5ab33fa9…f9e8`), llama.cpp b12024.

Artifacts: `results/sweeps/{offload2,concurrency,kvquality}/`.

## H2 — CPU/GPU offload boundary (Llama-3.2-3B, 28 layers)

llama-bench, ctx 2048, q8_0 KV, 5 repetitions, `-ngl` varied per cell:

| GPU layers | Prefill tok/s | Decode tok/s | Peak VRAM | Cell wall |
|---:|---:|---:|---:|---:|
| 99 | 473.7 | 29.18 | 2,364 MiB | 30.4 s |
| 32 | 470.6 | 29.06 | 2,364 MiB | 30.9 s |
| 24 | 453.8 | 21.71 | 2,074 MiB | 38.6 s |
| 16 | 435.6 | 15.21 | 1,612 MiB | 51.5 s |

**Finding:** the model has 28 layers, so `-ngl 32` and `-ngl 99` are the same
configuration — a useful sanity check that the sweep wires `-ngl` correctly
(prefill differs by 0.7%, decode by 0.4%).

Offloading the last 4 layers (24) saves **290 MiB** but costs **26% of decode
throughput**; dropping to 16 layers saves **752 MiB** and costs **48% of decode**.
Prefill degrades only 8% even at 16 layers. Partial offload is therefore a
decode-rate trade, close to linear: each MiB saved at the boundary costs roughly
0.06% decode.

## H4 — Concurrency (Qwen3-1.7B, two simultaneous clients, 4 rounds)

Each round fires two ~600-token requests together; `aggregate_rps` counts both.

| Server slots | Aggregate req/s | Round p50 | Slowest request | Request p50 |
|---:|---:|---:|---:|---:|
| 1 | 0.612 | 3,273 ms | 3,275 ms | 2,449 ms |
| 2 | 0.711 | 2,841 ms | 2,842 ms | 2,818 ms |

**Finding:** a second slot raises aggregate throughput **+16%** (0.612 → 0.711
req/s) and removes the 2× tail: with one slot the two requests serialize inside
the server (slowest ≈ 3.27 s); with two they overlap (both ≈2.84 s). The cost is
a higher per-request median at two slots (2,449 → 2,818 ms) because each request
now shares the GPU instead of queueing behind an idle one — the classic
throughput/latency knee.

The 4-slot cell produced no results artifact and is excluded rather than
reported from the sweep row alone. Root cause (found in the cell's run log): with
`--parallel 4` llama-server splits `--ctx-size` across slots (2048/4 = 512
tokens), and the 600-token probe prompt returns HTTP 400. The probe now records
that as an invalid round instead of aborting the cell, and the repeat wrapper
(`run-h4-repeat.sh`) uses ctx 8192 so each of the four slots gets 2048 tokens.
The 4-slot measurement and three repeat leases of the 1-slot configuration are
pending operator approval.

## KV quality at n=100 — q8_0 vs f16

ctx 4096, knowledge MCQ, same seed and items:

| KV | ARC acc | ARC acc_norm | HellaSwag acc | HellaSwag acc_norm |
|---|---:|---:|---:|---:|
| f16 | 0.470 | 0.470 | 0.440 | 0.470 |
| q8_0 | 0.470 | 0.480 | 0.420 | 0.480 |

**Finding:** the largest difference is 2 percentage points, well inside the
binomial noise at n=100 (SE ≈ 5 pp). No quality penalty is detectable; the
latency-only evidence from H1 is now backed by an accuracy comparison. This does
**not** prove q8_0 is lossless — it bounds the effect at this sample size.

## Tooling defects found while running these cells

1. `llama-bench` ignores `--ctx-size`/KV type, so bench-only sweeps cannot answer
   context questions (H1 fix: start the server per cell).
2. The sweep did not pass `-ngl` to `llama-bench`, so an offload sweep would have
   measured full offload in every cell (fixed and unit-tested).
3. `--parallel` and `--layers` were not wired through the entrypoint, producing
   cells named after the wrong axis (one wasted concurrency/offload run).
4. Model download in sweep mode used the default campaign spec instead of
   `SWEEP_BASE`, so the 3B model was never fetched (now fixed with an
   `huggingface_hub` fallback when the `hf` CLI is absent).

## Limitations

- One run per cell; no repeated leases, so between-run variance is unknown.
- The 3B model is a different architecture: numbers are not comparable to
  Qwen3-1.7B except within H2.
- Offload cells share the 3 GiB sandbox; host-RAM pressure is not separately
  measured.
- Concurrency used 2 clients and 4 rounds only; 4 slots is unmeasured.
- KV-quality comparison is one task pair at n=100 and cannot detect effects
  below ~10 pp.

## Decisions

- **q8_0 KV is now the default** for long-context work: 0.534× memory, no
  detectable accuracy change at n=100.
- **Partial offload is not worth it** on this card while the model fits: 24
  layers costs 26% decode for 290 MiB, and VRAM is already sufficient at 8192 f16.
- Concurrency on one slot should be avoided for latency-sensitive use; two slots
  give a better tail at +16% throughput.

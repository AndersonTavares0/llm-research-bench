# Batch size: null result at 512-token prompts (GTX 1050 Ti)

Question: do `--batch-size/--ubatch-size` change serving throughput on a 4 GiB
card at fixed context?

Artifacts: `results/campaigns/gpu-lab-conc-equiv-b{512,1024,2048}/`.

## Method

Qwen3-1.7B Q4_K_M, ctx 2048, 1 slot, q8_0 KV, `cache_ram 0`. Each cell ran
llama-bench (3 reps, 512-token prompts / 128-token decode) and the two-client
concurrency probe (6 rounds), with 1 Hz VRAM sampling.

| Cell | batch / ubatch | Prefill tok/s | Decode tok/s | 2-client req/s | p50 | Peak VRAM |
|---|---|---:|---:|---:|---:|---:|
| b512 | 512 / 128 | 860.6 | 48.08 | 0.612 | 2,470 ms | 1,340.1 MiB |
| b2048 | 2048 / 512 | 850.1 | 48.01 | 0.611 | 2,471 ms | 1,340.1 MiB |
| b1024 | 1024 / 256 | — | — | — | — | — |

The 1024/256 cell produced no artifacts: the payload wrote nothing and the
campaign was recorded as failed; it is excluded, not extrapolated.

## Finding

No measurable effect: prefill differs by 1.2% (860.6 vs 850.1 tok/s), decode by
0.15%, concurrency throughput by 0.2%, and peak VRAM is identical (1,340.1 MiB).
The prefill difference is within the run-to-run spread seen for the same
configuration elsewhere (H1 repeats had SD 1.9 tok/s on ~850 tok/s), so this is a
**null result for 512-token prompts**, not evidence that batching never matters.

## Why this is plausible

llama.cpp splits prefill into ubatches of the configured size; with a 512-token
prompt and ubatch 128 versus 512, the number of chunks changes but the total work
does not. Larger ubatches mainly help when the prompt is many times the ubatch
size, or when prompt processing dominates. At 512 tokens the GPU-side compute
buffers are also small enough that VRAM is unchanged.

## Next test that would actually resolve batching

Repeat with 2048- and 4096-token prompts at ctx 8192 (fits q8_0 at ~1,694 MiB),
comparing ubatch 128/256/512 for prefill tok/s and VRAM. That is a different
experiment from this one and should not be inferred from these numbers.

## Limitations

- Two valid cells only; the middle cell failed.
- Prompts too short to stress the batch split.
- One run per cell; no repeated leases.

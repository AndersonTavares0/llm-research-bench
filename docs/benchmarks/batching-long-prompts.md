# Batching with 2048-token prompts (GTX 1050 Ti)

Follow-up to `batching-null-result.md`, where 512-token prompts could not show a
batch effect. Here the prompt is 2048 tokens, ctx 8192 (q8_0 KV ≈ 1,694 MiB),
1 slot, 2 clients, 6 concurrency rounds, 3 bench repetitions, 1 Hz VRAM.

Artifacts: `results/campaigns/gpu-lab-conc-equiv-lb{128,256,512}/`.

| ubatch | Prefill tok/s (2k prompt) | Decode tok/s | 2-client req/s | p50 | Peak VRAM |
|---:|---:|---:|---:|---:|---:|
| 128 | 736.7 | 48.02 | 0.611 | 2,465 ms | 1,702.1 MiB |
| 256 | 751.3 | 47.95 | 0.610 | 2,484 ms | 1,702.1 MiB |
| 512 | 733.3 | 48.03 | 0.612 | 2,463 ms | 1,702.1 MiB |

## Finding

No monotonic batch effect: the three prefill values span 2.4% in the order
736.7 → 751.3 → 733.3, i.e. the middle cell is fastest and the largest ubatch is
not better. Decode, concurrency throughput and VRAM are flat to within 0.2% /
0.2% / 0 MiB.

The prefill rate at 2048 tokens (~740 tok/s) is **14% lower** than at 512 tokens
(~860 tok/s, measured in the previous experiment). That is a context-length
effect (attention over a longer prefix), not a batching effect, and it is
consistent across all three ubatch settings.

## Limitations

- One run per cell; a ≤2% effect cannot be separated from run noise.
- Only one prompt length (2048) and one ctx (8192).
- Three repeat attempts were refused during the drain window; the successful
  cells were obtained by warming the gateway with `/health` and waiting ~60 s
  between leases.

## Conclusion

For this model and card, `--ubatch-size` is not a useful throughput knob at
512–2048-token prompts; the measurable lever remains context length. Do not tune
ubatch without repeated runs at a larger effect size.

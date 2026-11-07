# Context length and chunk position jointly affect version selection

## Question

The two-version prose panel scored 9/10 with the correct chunk second in a 551-token prompt, but at roughly 7,271 tokens accuracy fell to 7/10 for adjacent chunks. We added intermediate context sizes and moved the same adjacent pair through the long context to determine whether there is a simple length threshold or a positional effect.

All panels reuse the same two prose chunks, instruction, and query. The newest version (`2025-08-21`, designated code) and older version (`2024-12-08`, `M1P6Z4`) swap order between baseline and challenge. Only filler count or pair placement changes.

## Results

### Increasing filler count; pair at approximately 45% of the filler rows

| Filler rows | Prompt tokens | Baseline (newest first) | Challenge (newest second) |
|---:|---:|---:|---:|
| 20 | 551 | 8/10 | 9/10 |
| 40 | 971 | 10/10 | 5/10 |
| 80 | 1,811 | 10/10 | 2/10 |
| 160 | 3,491 | 10/10 | 2/10 |

At 40 rows, baseline was 10/10 and challenge 5/10; every challenge miss returned the older `M1P6Z4`. At 80 rows, baseline 10/10 and challenge 2/10; 8/10 challenges returned `M1P6Z4`, while two selected the designated code. At 160 rows, baseline 10/10 and challenge 2/10; 8/10 returned `M1P6Z4` and two returned the designated code. At 20 rows the earlier study found 8/10 and 9/10 respectively, with the three total misses following the older version rather than position.

### Moving the adjacent pair within the 340-row long context

| Pair start index | Prompt tokens | Baseline | Challenge |
|---:|---:|---:|---:|
| 30 | 7,271 | 10/10 | 4/10 |
| 170 | 7,271 | 10/10 | 7/10 |
| 310 | 7,271 | 10/10 | 1/10 |

Every challenge miss at indices 30 and 310 emitted the older chunk's `M1P6Z4`; at index 170, all three misses also emitted `M1P6Z4`. Thus near 7k tokens, the model mostly follows the first member of the pair, and the size of that effect depends on where the pair appears. The late pair was especially difficult when the newest chunk came second.

All studies used Qwen3-1.7B Q4_K_M, llama.cpp build 12024, ctx8192, q8_0 K/V, temperature 0, GEN=512, THINK=false, one client, seed 42. Each 10-target suite ran in two disjoint five-target leases. The final 20 rows per suite had exact token-count parity and zero padding; all responses ended `stop` with no `reasoning_content`. Peak sampled VRAM was 1,702.1 MiB.

## Interpretation

The results do **not** support one clean monotonic context-length threshold. The 551-token panel is mostly content-based, but increasing filler to 971 tokens drops challenge accuracy to 5/10; 1,811 and 3,491 tokens are both 2/10. At the same long prompt length, changing only pair placement yields challenge accuracy from 1/10 to 7/10. So context length and absolute/relative placement interact; the observed failure is not explained by duplicate count alone, nor by a single cutoff.

For this model and format, the practical trend remains: short prompts often allow two dated versions to be compared, whereas longer prompts can make the first chunk dominate, especially when the correct version is second. Keep duplicate history out of long retrieval contexts when feasible; otherwise consolidate versions or make the desired evidence locally unambiguous. These are bounded observations on one quantized model and synthetic filler, not a universal threshold.

## Reproducibility

Artifacts:

- `results/campaigns/gpu-lab-longctx-needle-compact-context-conflict-b{0,1}/` (40 fillers, 971 tokens)
- `results/campaigns/gpu-lab-longctx-needle-mid-context-conflict-b{0,1}/` (80 fillers, 1,811 tokens)
- `results/campaigns/gpu-lab-longctx-needle-long-context-conflict-b{0,1}/` (160 fillers, 3,491 tokens)
- `results/campaigns/gpu-lab-longctx-needle-early-pair-conflict-b{0,1}/` (pair at index 30)
- `results/campaigns/gpu-lab-longctx-needle-late-pair-conflict-b{0,1}/` (pair at index 310)

Intermediate leases were generations 333/334 (80 rows), 335/337 (160 rows; generation 336 was boundary-refused and recovered without running), 338/339 (40 rows), 341/342 (index 30; generation 340 was boundary-refused and recovered), and 343/344 (index 310). Each successful lease restored production and passed the real inference recovery check. The original experiment config hash remained `b29b4113efb432f3ea3b3b6de62ef88bd596eec99e602b023c1c1c915c3c00f2`; per-lease deadline remained 400 seconds.

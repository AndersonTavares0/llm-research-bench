# Evidence index

This index points to the strongest currently documented findings, not a
leaderboard. The repo contains exploratory, fixed-item experiments on one
GTX 1050 Ti; repeated deterministic outputs are consistency checks, not
independent hardware or item samples. Read each linked report for full methods,
uncertainty, caveats, and raw artifacts.

| Conclusion | Evidence / protocol | Sample and result | Main limit | Raw evidence |
|---|---|---|---|---|
| Raising the completion cap fixed observed truncations in the long-context schema suite. | [Generation-budget full30](generation-budget-longctx-full30.md); same 30 prompts, cap 256 vs 512. | 24/30 → 30/30 valid; all 6 failures at cap 256 ended `length`, then completed at 261–321 tokens; paired exact McNemar p=.03125. | One deterministic 30-item set/model/config; establishes these failures, not universal cap behavior. | [`audit-reason-256`](../../results/campaigns/gpu-lab-longctx-audit-reason-256/), [`reason-512-full30`](../../results/campaigns/gpu-lab-longctx-reason-512-full30/) |
| JSON Schema response formatting outperformed generic JSON-object formatting for this exact extraction suite. | [Constraint-format 7k](constraint-format-7k.md); same 30 cases, only response format changed. | Schema 30/30 in each run; `json_object` 18/30 in each; 12/0 discordance, p=.000488 (n=30 pairs, not 60 independent cases). | Schema validity is not semantic correctness; one prompt/model family; repeated deterministic run. | [`json-schema`](../../results/campaigns/gpu-lab-longctx-grammar7k-json-schema/), [`schema repeat`](../../results/campaigns/gpu-lab-longctx-grammar7k-json-schema-r2/), [`json-object`](../../results/campaigns/gpu-lab-longctx-grammar7k-json-object/), [`json-object repeat`](../../results/campaigns/gpu-lab-longctx-grammar7k-json-object-r2/) |
| Native tool calling was reliable on the fixed probe set; JSON-mediated variants were not. | [Tool calling at long context](tool-calling-long-context.md); 3 tools, fixed prompts, multiple context sizes. | Native 18/18; JSON-mediated variants 2–8/18. | Interfaces/prompts/schemas differ, so not a clean grammar-only causal comparison; fixed synthetic cases. | [`native ~1.9k`](../../results/campaigns/gpu-lab-toolctx-n1900/), [`native ~3.8k`](../../results/campaigns/gpu-lab-toolctx-n3800/), [`native ~7k`](../../results/campaigns/gpu-lab-toolctx-n7k/), [`JSON variants`](../../results/campaigns/gpu-lab-toolctx-j1900/) |
| q8_0 KV reduces sampled VRAM substantially; quality evidence is mixed/underpowered. | [KV needle retrieval](kv-precision-needle-retrieval.md); [7k audit/correction](kv-precision-7k.md); [paired quality](lease-deadline-and-kv-paired.md). | Needle panel 30/30 both f16 and q8_0; peak 2,118.1 → 1,702.1 MiB (-416 MiB, -19.6%). ARC n=20: .35→.40; HellaSwag n=20: .40→.40. | Needle ceiling cannot bound subtle loss; 7k legacy evaluator lacked usage/finish metadata; quality study has low n and p=1 does not imply equivalence. No consistent latency gain established. | [`f16 d10`](../../results/campaigns/gpu-lab-longctx-needle-kv-f16-d10/), [`q8 d10`](../../results/campaigns/gpu-lab-longctx-needle-kv-q8-d10/), [`f16 d50`](../../results/campaigns/gpu-lab-longctx-needle-kv-f16-d50/), [`q8 d50`](../../results/campaigns/gpu-lab-longctx-needle-kv-q8-d50/), [`f16 d90`](../../results/campaigns/gpu-lab-longctx-needle-kv-f16-d90/), [`q8 d90`](../../results/campaigns/gpu-lab-longctx-needle-kv-q8-d90/) |
| Repeated same-ID versions can make answer selection depend on order in long synthetic-filler contexts. | [Context length/position transition](needle-context-length-transition.md), read with [prose conflict](needle-prose-conflict.md) and [pair-count conflict](needle-pair-count-conflict.md). | Ten fixed cases per suite. At 7,271 tokens, challenge was 4/10, 7/10, 1/10 for pair starts 30/170/310; at 551 tokens it was 9/10. | Not a universal length threshold; one model, repeated filler, small fixed set, position interacts with length. | [`position b0`](../../results/campaigns/gpu-lab-longctx-needle-position-conflict-b0/), [`position b1`](../../results/campaigns/gpu-lab-longctx-needle-position-conflict-b1/), [`prose b0`](../../results/campaigns/gpu-lab-longctx-needle-prose-conflict-b0/) |
| Explicit dates/status/rules were not reliably applied in tested long synthetic panels; literal query overlap was associated with better retrieval. | [Precedence](needle-precedence-conflict.md), [status label](needle-status-label-conflict.md), [authoritative literal](needle-authoritative-literal-conflict.md). | Challenge exact ranged 0/10 (date/flag without literal cue) to 10/10 with literal `"authoritative": true`. | Multiple related exploratory panels, same ten IDs/prompt family; this association does not prove an internal string-matching mechanism. | [`precedence b0`](../../results/campaigns/gpu-lab-longctx-needle-precedence-conflict-b0/), [`status b0`](../../results/campaigns/gpu-lab-longctx-needle-status-label-conflict-b0/), [`literal b0`](../../results/campaigns/gpu-lab-longctx-needle-authoritative-literal-conflict-b0/), [`literal b1`](../../results/campaigns/gpu-lab-longctx-needle-authoritative-literal-conflict-b1/) |
| Partial GPU offload trades throughput for VRAM; 1 vs 4 slots increased throughput in one repeated concurrency study. | [Offload and early concurrency](h2-h4-kv-results.md); [concurrency repeats](h4-concurrency-repeats.md). | Llama-3.2-3B offload: 99→24 layers saves 290 MiB at ~26% lower decode; 16 layers saves 752 MiB at ~48% lower decode. 1→4 slots: +20.4% aggregate req/s across 3 leases/arm. | Different model/setup from Qwen studies; concurrency changes per-slot context 8192→2048, so not context-equivalent; n=3 leases is weak. | [`offload sweep`](../../results/sweeps/offload2/), [`concurrency repeats`](../../results/sweeps/h4-par1-r1/), [`4-slot repeats`](../../results/sweeps/h4-par4-r3/) |
| Official-task scores are integration evidence, not model rankings. | [Official campaigns](official-campaigns.md). | Zero-shot deterministic first-100 scores with Wilson item intervals; separate n=20 smoke. | Not full/random task splits; GSM8K protocol differs from default few-shot; EOS/template and host-resource caveats apply. | [`Qwen3-1.7B v2`](../../results/campaigns/gpu-lab-qwen3-1.7b-v2/), [`smoke`](../../results/campaigns/smoke-qwen3-1.7b-v1/) |

## Open evidence gap

The source-pinned fixture supports a planned 100-item study; only 15 paired
questions across three of twenty batches completed before GPU work was halted.
The partial outcomes are descriptive and not a representative estimate. A
subsequent operational check passed the production real-completion verifier but
did not resolve the historical GGUF-path discrepancy; no new batch followed.
See the
[interrupted pilot report](hotpotqa-support-order-partial.md) for per-batch
metrics, raw artifact hashes, and the operational stop reason. Protocol: 50
bridge + 50 comparison (all labeled hard), interleaved into twenty five-question
batches; all ten supplied candidate passages remain in each prompt. The paired
condition moves support passages from first to last while preserving order
within each group. Both prompts are counted with the serving tokenizer and
padded to exact input-token parity; generation order alternates by item. Primary
outcome is normalized answer exact match; secondary outcomes are supporting-title
F1 and joint exact. This is closed-context multi-hop QA, not live retrieval or
version-history conflict resolution. Source-title overlap is low but nonzero. See
[`data/rag/README.md`](../../data/rag/README.md), the fixture manifest, and
[`rag_evaluator.py`](../../src/llm_research_bench/rag_evaluator.py).

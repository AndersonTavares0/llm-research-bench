# Research roadmap: small LLMs on a 4 GiB GTX 1050 Ti

This page turns the measured evidence into a prioritized experiment plan. It does
not replace the campaign records; every claim below points at an artifact.

## What is already established (measured)

- **Throughput ceiling.** Qwen3-1.7B Q4_K_M, llama.cpp b12024, 6 threads:
  848.835 tok/s prefill (512) and 48.030 tok/s decode (128), SD 1.892 / 0.015,
  n=10. Artifact: `results/campaigns/gpu-lab-qwen3-1.7b-v2/.../llama-bench/`.
- **Quality at n=100, zero-shot.** ARC 0.470, HellaSwag 0.470 (acc_norm),
  GSM8K 0.460 flexible-extract, IFEval 0.680 prompt-strict. Not a ranking.
- **Memory envelope.** The Q4_K_M server held 1.21–1.61 GiB of the 4096 MiB card
  during evaluation (spot checks). The lab sandbox caps host RAM at 3 GiB and
  killed the server when llama.cpp's host prompt cache grew (generation 167).
- **Operational ceiling.** The lease controller preempts production, restores it,
  and survives supervisor death during acquisition (7/7 self-tests).

## What remains worth researching

1. **Natural-document RAG groundedness is the largest evidence gap.** The
    existing needle suites use ten fixed IDs and synthetic repeated filler. They
    establish prompt-family failure modes, not field reliability. The
    source-pinned 100-item HotpotQA study completed only 15 paired cases across
    batches 0–2 of 20 before it was halted. This is an incomplete descriptive
    pilot, not a confirmatory result. The dataset supplies candidate passages:
    it tests closed-context multi-hop QA, not live retrieval or version-history
    conflicts. See the [partial report](hotpotqa-support-order-partial.md).
    Do not resume GPU work until an operator repairs the missing production model
    and the authoritative real-completion verifier passes.
2. **Generalization across models and retrieval systems is unknown.** Current
   conflict findings use Qwen3-1.7B Q4_K_M, one runtime, one GPU and hand-built
   candidate orderings. Replicate only after the natural-document protocol is
   validated, and distinguish model, prompt, retrieval order and context length.
3. **Concurrency and host-cache policies are only partially characterized.**
   H4 has repeated 1-vs-4-slot results, not the complete 1/2/4 grid at equal
   per-request context. The host-cache OOM led to `--cache-ram 0`, but no
   randomized cache-size trade-off study was completed.
4. **Offload results are model-specific.** See [`h2-h4-kv-results.md`](h2-h4-kv-results.md);
   do not infer a general CPU/GPU boundary from one model or one lease per cell.
5. **Historical quality, safety and tokenizer claims need current provenance.**
   Keep their original reports, but treat them as exploratory unless the linked
   protocol, exact sample and raw outputs support the particular claim.

## Hypotheses and designs

Each row is one campaign spec per configuration. Preserve paired/order-randomized
designs where meaningful and report run-level variation separately from item
variation. All GPU inference must run through the gpu-lab lease controller because
it preempts production; keep its watchdog, deadline, isolation, cleanup and
verified recovery gates intact.

### H1 — KV cache dominates the usable context window (highest value)

- Configs: ctx {2048, 4096, 8192}; KV {f16, q8_0} → 6 cells, one lease each.
- Measure: `nvidia-smi` 1 Hz memory used, prefill/decode tok/s at 512/128 and at
  a long prompt (ctx-64), and a fixed 100-item MCQ slice for quality drift.
- Analysis: memory vs ctx linear fit; compare with the analytical 112 KiB/token;
  report the largest ctx that fits 4096 MiB with ≥256 MiB headroom.
- Decision rule: q8_0 KV is adopted for long-context work only if memory drops
  ≥35% and the MCQ score change is inside the paired-bootstrap interval.
- Status: **executed** (lease generation 172) — memory slope 113.0 KiB/token f16,
  60.3 KiB/token q8_0, fixed cost ~1,206 MiB. See
  [`h1-context-kv-results.md`](h1-context-kv-results.md).
- Runner: `tools/homelab/run-sweep.sh` expands the grid with
  `llm_research_bench.sweep`, runs each cell through `run_campaign` inside one
  lease, samples GPU memory at 1 Hz, and `sweep analyze` joins the throughput
  from each cell's `llama-bench/results.json`.

### H2 — Offload boundary

- Configs: `n_gpu_layers` {99, 32, 24, 16} on Qwen3-1.7B and Llama-3.2-3B.
- Measure: prefill/decode throughput and peak memory; report the layer count where
  decode throughput collapses.
- Decision rule: publish the throughput/VRAM frontier; no model ranking.

### H3 — Host prompt cache policy

- Configs: `cache_ram` {0, 256, 1024} MiB, repeated identical prompts vs distinct.
- Measure: time-to-first-token for cache hits, peak host RSS, OOM events.
- Decision rule: recommend the largest cache that never exceeds 80% of the 3 GiB
  sandbox budget.

### H4 — Concurrency

- Configs: `--parallel` {1, 2, 4} at ctx 2048 with q8_0 KV.
- Measure: aggregate decode throughput and p50/p95 latency; report the
  throughput/latency knee.
- Analysis: paired within-lease ordering, because concurrency changes queueing.

### H5 — Capability probes (structured output, tool calling, closed-context QA)

- Wire the existing evaluators into the campaign output schema (no new engine).
  `llm_research_bench.capability` now ships deterministic `structured_output`
  and `tool_call` probes and is reachable as a `backend: capability` task group.
- Tasks: JSON-schema adherence, tool-call argument validity, and the new paired
  HotpotQA closed-context answer/evidence-order probe. The latter uses supplied
  candidate passages; it does not measure a retriever or version conflicts.
- Decision rule: report per-task pass rates with Wilson intervals; no composite
  score.
- Status: structured output and tool calls have exploratory smoke results on
  Qwen3-1.7B (10/10 and 5/5, respectively); HotpotQA evaluator and fixture are
  implemented. Only 15/100 paired HotpotQA items (batches 0–2/20) ran; treat
  these as an incomplete descriptive pilot, halted after the production recovery
  verifier returned HTTP 500 because `/models/Qwen3.5-4B-Q4_K_M-MTP.gguf` was
  missing. The source supplies candidates, so this is closed-context QA, not
  retrieval or version-conflict evidence. See the
  [partial report](hotpotqa-support-order-partial.md). No more GPU leases until
  production is repaired and the authoritative verifier passes.
- Campaign spec: `configs/campaigns/gpu-lab-capability-probe.yaml` runs both
  probes as `backend: capability` groups under one lease; each response is timed
  client-side and reported as p50/p95 end-to-end latency.
- Status: probes smoke-tested against the production Qwen3.5-4B endpoint
  (5/5 structured outputs, 3/3 tool calls valid). That is an evaluator check on a
  different model, not a campaign result for Qwen3-1.7B.

## Protocol constraints

- Preregister the hypothesis, primary metric and comparison family before each
  campaign; state the MDE (~20 pp at n=100 for proportions near 0.5).
- Publish raw JSON, the spec, hashes, runtime versions and the analysis script.
- Never merge hardware profiles; the local RTX 3060 Ti artifacts remain separate.
- Every GPU experiment must use the approved gpu-lab job path, current per-lease
  deadline, controller watchdog and production recovery verification. Do not
  bypass the gateway or weaken safety checks. Preserve raw requests/responses,
  model/runtime/data hashes and terminal lease state. Do not push, merge or deploy
  without explicit authorization.

## Candidate models (already present in the lab model store)

| Model | Quantization | Why it is interesting |
|---|---|---|
| Qwen3-1.7B | Q4_K_M | baseline; full Q4/Q8 comparison already measured |
| Llama-3.2-3B-Instruct | Q4_K_M | larger footprint, tests the 4 GiB boundary |
| SmolLM2-1.7B-Instruct | Q4_K_M | same size class, different architecture |
| Qwen2.5-0.5B | Q4_K_M | lower bound for throughput and quality |

Do not add models until H1/H2 show where the memory boundary is; adding models
before that multiplies cost without answering the constraint question.

In-service measurements (no lease) are recorded in
[`in-service-probe.md`](in-service-probe.md).

## Verified model sources (Hugging Face API, 2026-11-05)

| Repo | Revision | Q4_K_M file | Bytes | License |
|---|---|---|---|---|
| `unsloth/Qwen3-1.7B-GGUF` | `d7f544eead698dbd1f15126ef60b45a1e1933222` | `Qwen3-1.7B-Q4_K_M.gguf` | 1,107,409,472 | apache-2.0 |
| `bartowski/Llama-3.2-3B-Instruct-GGUF` | `5ab33fa94d1d04e903623ae72c95d1696f09f9e8` | `Llama-3.2-3B-Instruct-Q4_K_M.gguf` | 2,019,377,696 | llama3.2 |
| `Qwen/Qwen3-1.7B-GGUF` | `90862c4b9d2787eaed51d12237eafdfe7c5f6077` | none (Q8_0 only in this repo) | — | apache-2.0 |

The official SmolLM2-1.7B-Instruct and Qwen2.5-0.5B-Instruct GGUF repos did
**not** list a `Q4_K_M` file under the usual name in the same query, so they are
not planned until their quant naming is checked. Do not add a model whose file
name, revision and hash have not been verified.

## Running H2 and H4

```bash
# CPU/GPU boundary (downloads Llama-3.2-3B on first use, ~2.0 GB)
python -m llm_research_bench.sweep generate \
  --base configs/campaigns/gpu-lab-offload-llama32-3b.yaml \
  --grid ctx=2048 --kv q8_0 --layers 99,32,24,16 --out /workspace/results/sweeps/offload

# Concurrency: latency p50/p95 from the capability probes
python -m llm_research_bench.sweep generate \
  --base configs/campaigns/gpu-lab-concurrency-qwen3.yaml \
  --grid ctx=2048 --kv q8_0 --parallel 1,2,4 --out /workspace/results/sweeps/concurrency
```

`sweep analyze` attaches `peak_vram_mib`, `prefill_tok_s`, `decode_tok_s` and a
`latencies` block per capability suite, so one table covers memory, throughput
and end-to-end latency for every cell.

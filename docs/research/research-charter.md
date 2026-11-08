# SLM-Limits research charter

**Central question.** What are the practical limits of Small Language Models
(≈0.5B–4B parameters) on legacy constrained hardware — primarily one
GTX 1050 Ti with 4096 MiB VRAM, with a separate RTX 3060 Ti station used
only for the offline exploratory routing replay — and how can their
efficiency, capabilities, reliability, and security be improved within those
limits?

This charter consolidates the repository's scientific direction: what is
known (with evidence labels), what is uncertain, the prioritized research
questions, and the next experiments worth running. It does not replace the
per-campaign records, the two compiled reports
(`reports/en-US/report_en-US.pdf`, `reports/pt-BR/report_pt-BR.pdf`), the
[evidence index](../benchmarks/evidence-index.md), or the
[operational roadmap](../benchmarks/research-roadmap.md); every claim points
at an artifact, and this charter links to them.

Evidence labels used below (per `AGENTS.md`):
**measured** = recorded in `results/` on the real hardware (single-host,
exploratory unless stated); **partial** = measured but incomplete (e.g.,
ongoing designs, halted campaigns); **analytical** = computed model
assumptions, not instrumentation; **ready** = benchmark/protocol implemented
and deterministically tested, but **no model has been run**; **unknown** =
not studied here.

## Hardware and fixed context

- Primary host: GTX 1050 Ti (4 GiB GDDR5, 112 GB/s theoretical), llama.cpp
  (pinned b12024); Ollama-era historical artifacts are kept separate from
  gpu-lab campaigns.
- A separate RTX 3060 Ti station contributes only the offline exploratory
  routing replay (Q4_K_M vs Q8_0, `results/analysis/quant-cascade-oracle-v1.json`).
  Its raw campaign files remain unmerged, and no hardware profile or
  measurement is pooled with the GTX 1050 Ti program.
- Repeated queries within one hardware run are descriptive observations,
  **not** independent replicates; hardware-level statistical inference is
  not supported by them. Welch/Mann-Whitney machinery exists but is
  fail-closed (`statistical_analysis.run_full_statistical_analysis`) until
  independent randomized runs exist.
- Execution gates: every GPU experiment runs through the gpu-lab lease
  controller (watchdog, deadline, isolation, cleanup, verified recovery);
  model runs are additionally blocked right now until the current
  route/isolation/cleanup/recovery controls are re-verified.

## 1. What the repository already knows

### Demonstrated (measured, explanatory; single-host unless noted)

- **Inference envelopes.** Eight SLM configurations measured end-to-end
  (0.5B–4B): throughput/VRAM/temperature telemetry at 250 ms
  (`system_performance/system_metrics.json`); e.g., Qwen3.5-2B 37.6 tok/s at
  1580.7 MiB vs Qwen3.5-4B 18.6 tok/s at 3140.7 MiB. Descriptive ablation on
  Gemma-4: IQ4_XS +28.2% and MTP +25.6% decode throughput vs baseline, net
  VRAM +40.0 MiB for the combined configuration — query repeats, not
  independent replicates.
- **Throughput ceiling pattern.** Solo campaign: Qwen3-1.7B Q4_K_M
  848.8 tok/s prefill (512) / 48.0 tok/s decode (128), n=10
  (`gpu-lab-qwen3-1.7b-v2`).
- **KV cache physics.** H1 executed: memory slope ≈113.0 KiB/token (f16) vs
  60.3 KiB/token (q8_0), fixed cost ≈1206 MiB; q8_0 KV cut sampled peak VRAM
  −19.6% with needle panel 30/30 intact in both formats
  (`h1-context-kv-results.md`, `kv-precision-needle-retrieval.md`).
- **Quality microbenchmarks (integration evidence only).** First-100
  zero-shot: ARC .470, HellaSwag .470, GSM8K .460 (flex), IFEval .680
  prompt-strict — not a ranking.
- **Formatting/robustness regularities (paired, fixed items).** JSON Schema
  formatting 30/30 vs `json_object` 18/30 (12/0 discordant, p=.000488);
  native tool calling 18/18 vs JSON-mediated 2–8/18; raising completion cap
  256→512 fixed 24/30→30/30 truncation (McNemar p=.03125). Exploratory;
  deterministic items.
- **Partial GPU offload frontier.** Llama-3.2-3B: 99→24 layers = −290 MiB for
  ~26% lower decode; 16 layers = −752 MiB for ~48% lower decode
  (model-specific; not a general boundary).
- **Concurrency direction.** 1→4 slots: +20.4% aggregate req/s across
  3 leases/arm, under equal-context studies only partially completed. Host
  prompt-cache OOM led to `--cache-ram 0` as the safe precedent (H3 not
  executed).
- **Thermal/clock behavior.** 311.58 s campaign: 44→74 °C die, clocks
  1695→1607 MHz (−5.2%); thermal drift is a real confound for long runs.
- **Memory feasibility analytics.** Candidate catalog VRAM budgeting (7
  models); Gemma-3-4B-style configs exceed 4096 MiB; Kn cache math and
  Roofline *proxies* are analytical, not measured bus utilization.
- **Failure-mode structure in long synthetic contexts.** Order-dependence on
  repeated same-ID fillers, precedence/status-rule application unreliability,
  literal-cue dependence (`needle-*` panels; fixed 10-case suites).
- **Defensive security posture (human-workflow sides are ready; model side
  unmeasured).** Three deterministically scored benchmarks exist with a
  validated result schema (`configs/schemas/defensive_cyber_results.v1.schema.json`):
  static CWE triage v2 (hand-authored labels, no independent adjudication),
  CVE advisory triage v1 (labels were independently verified against NVD
  2.0/MITRE/upstream advisories on 2026-11-08 with per-case
  `label_provenance`; the nonexistent nginx CVE-2016-0748 case was
  redirected to the substantiated CVE-2016-0747, and boundary regressions
  are test-locked — labels are no longer purely comparator-derived, though
  no blinded second reviewer has relabeled them), and the appsec chatbot
  scenarios (expected outcomes follow the enforcement design by
  construction; per-call `call_reports` now distinguish authorized
  execution from blocks, and weakened enforcement cannot fabricate a
  clean authorized result). Plus historical exploratory probes
  (over-refusal 0/4, CI [0%, 60.2%]; injection ASR ≈50–100%; harness
  intercept 2/2), single-run. **No model has ever been run against the new
  benchmarks**; transcripts are scripted author-written proposals.

### Partially supported (started, incomplete, or blocked)

- HotpotQA support-order paired study: 15/100 items (3/20 batches) before
  operational halt; the only natural-document (non-synthetic-filler) RAG
  evidence, and it is explicitly a pilot.
- Concurrency equal-context grid: repeats on 1-vs-4 arms; full 1/2/4 grid +
  batch variants incomplete.
- KV-quant quality: q8_0 needle performance confirmed, but quality side
  (n=20 ARC/HellaSwag) underpowered; p=1 does not imply equivalence.
- Sampling: everything so far is deterministic greedy (τ=0, seed 42);
  temperature/top-p effects on quality and refusal behavior are untested.
- Statistical inference: method skeleton exists but fail-closes; no
  independent random replicate campaign yet, so no confirmatory evidence
  anywhere in the repo.

### Unknown / not explored here

- **Adaptation (entire area):** fine-tuning, LoRA/QLoRA, distillation,
  compression beyond quantization, data quality, generalization,
  catastrophic forgetting — no experiments.
- **Model selection comparisons:** no measured generalist-vs-specialist
  contrast (the security specialist review found no validated candidate);
  multimodal models unexplored (no vision inputs in any benchmark); the four
  studied configurations are compared descriptively, not as a selection
  study.
- **Model routing, ensembling, cascades:** unexplored.
- **Energy:** no power measurement exists (no wattmeter); energy-efficiency
  figures in legacy artifacts are unverified and are treated as not
  measured.
- **Hallucination/calibration:** no calibration study (confidence vs
  accuracy); only indirect evidence via QA exact-match.
- **Inference infra CVE exposure of the stack itself:** tracked as a separate
  hygiene question; not measured.

## 2. Research questions (deduplicated; 24 total)

Each RQ is measurable and maps to one primary metric; duplicates across
areas were merged. Six tracks: A (5 RQs), B (6), C (2), D (3), E (4),
F (4). Evidence status: ①measured · ②partial · ③analytical ·
④ready · ⑤unknown.

### Track A — Inference efficiency

- **RQ-A1 (context×memory frontier).** For each quantized SLM, what maximum
  context (with ≥256 MiB headroom) fits 4096 MiB, and how do KV
  quantization and seq-parallel/slot settings move that frontier? — ① for
  Qwen3-1.7B (H1); ⑤ for other configurations.
- **RQ-A2 (compute–memory regime).** Is batch-1 decode memory-bandwidth-bound
  under speculative MTP, and does multi-token generation change effective
  arithmetic intensity? — ③ only (Roofline proxy; no DRAM instrumentation).
- **RQ-A3 (offload boundary generality).** How does the CPU↔GPU layer
  offload frontier vary across tokenizers/architectures and KV formats? — ①
  for Llama-3.2-3B one config; ⑤ otherwise.
- **RQ-A4 (concurrency knee).** What concurrent-load knees (aggregate
  vs perrequest latency) appear at equal per-request context across
  1/2/4 slots and batch variants? — ② (partial grid).
- **RQ-A5 (energy).** What is the energy per request / per token under real
  serving loads? — ⑤ (requires a power meter; no supported estimate exists).

### Track B — Behavior & reliability

- **RQ-B1 (reasoning–budget interaction).** Which reasoning prompts exceed
  completion budgets and fail silently at given context/quantization
  settings, and at which length/format? — ② (cap fix measured on 30 items;
  systematic budget study unexplored).
- **RQ-B2 (structured-output & tool-calling reliability).** Which output
  formats maximize valid JSON/tool calls at long context? — ① for schema vs
  json_object and native vs JSON mediation; ⑤ beyond.
- **RQ-B3 (long-context robustness).** How do distractors, precedence
  conflicts, and literal cues interact in natural (not synthetic-filler)
  documents? — ② (synthetic panels measured; natural-document pilot 15/100
  halted).
- **RQ-B4 (sampling-parameter effects).** How does decoding temperature /
  top-p change quality, refusal behavior, and stability at fixed seed?
  — ⑤ (all evidence so far is greedy).
- **RQ-B5 (calibration/hallucination).** Do confidence statements or answer
  formats track accuracy (calibration), and what are hallucination rates by
  task type under VRAM-constrained serving? — ⑤.
- **RQ-B6 (multilingual viability).** How do tokenizer fertility ratios
  translate into effective context budgets and multilingual task quality? —
  ① for token ratios (12 texts), ⑤ for quality translation (sensitive-topics
  protocol specified but not executed).

### Track C — Adaptation

- **RQ-C1 (post-training at 4 GiB).** Can SFT/LoRA/QLoRA adaptation of a
  ≤2B model run on this host at all, and what capability deltas/distillation
  gains result? — ⑤ entirely.
- **RQ-C2 (adaptation vs forgetting).** Do the above trade targeted-capability
  gains against other-behavior regressions (catastrophic forgetting)? — ⑤.

### Track D — Model selection

- **RQ-D1 (quality/resource trade-off).** At matched VRAM, does a smaller
  generalist outperform a larger offloaded one (per-task utility, not just
  throughput)? — ③/① fragments (catalog analysis + throughput tables); no
  matched-quality paired study.
- **RQ-D2 (specialists).** Do security/domain-specialist SLMs measurably
  outperform generalists on defensive tasks, with auditable provenance? —
  ④ (benchmarks exist; no specialist run; no candidate validated).
- **RQ-D3 (multimodal on 4 GiB).** Are any vision-language SLMs feasible and
  worthwhile here, and at what VRAM/latency? — ⑤ (none cataloged with
  verified GGUF budgets).

### Track E — Security

- **RQ-E1 (defensive static analysis).** How accurately and consistently
  can SLMs triage CWE weaknesses and CVE advisories on versioned
  inventories (with correct abstention)? — ④ (deterministic scoring ready;
  zero model runs).
- **RQ-E2 (application security boundary).** Under injection/untrusted input
  through an SLM app, which unauthorized proposals get blocked vs permitted,
  and at what false-refusal cost? — ④ (harness ready; historical exploratory
  probes ① only).
- **RQ-E3 (mitigation effectiveness).** Which mitigation layers
  (instructions, authz enforcement, strict schemas, separation, quotas) move
  security outcomes vs task success/latency? — ④ partial (see limitations):
  two enforced-and-tested knobs exist in the harness
  (`authorization_enforcement` on document/diagnostic/credential tools, and
  the per-session call quota behind the `sandboxing_timeouts_quotas` field —
  the field name promises more than the code delivers: no actual sandboxing
  or timeouts are implemented), while `system_instructions`,
  `strict_tool_schemas`, and `trusted_untrusted_separation` are declared
  config fields with **no enforcement logic** (`wrap_untrusted` is a tested
  standalone helper not wired into any tool flow); no measured contrast, and
  the instruction-following layer additionally requires model runs.
- **RQ-E4 (alignment limits).** What is the over-refusal vs compliance
  frontier for defensive-but-scary prompts under constrained serving? — ①
  exploratory (0/4 benign; ASR ≈50–100% on injections); no frontier study.

### Track F — Practical utility

- **RQ-F1 (usable RAG).** Does support ordering and candidate-pool design
  change groundedness on natural multi-hop documents at context extremes? —
  ② (15/100 pilot).
- **RQ-F2 (tool-use reliability).** What tool-selection/argument error rates
  persist across context sizes, formats, and models in realistic mock
  environments? — ② (mock suites exist; a composed end-to-end study is not in
  the repo).
- **RQ-F3 (routing).** When does a router (by task, budget, language)
  outperform single-model deployment on this hardware? — ⑤.
- **RQ-F4 (viability thresholds).** Which of the five measured
  configurations qualify as local research-only vs assistive-grade vs
  production-grade under documented acceptance criteria (accuracy, latency,
  safety)? — ③/① (viability dossier exists; no task-utility measurements to
  apply it to).

## 3. Methodological weaknesses to fix (cross-cutting)

1. **No independent replication layer.** All throughput/quality evidence is
   single-run or within-run repeats; run full campaigns only via the
   gpu-lab lease path and add ≥2 independent lease replicates per cell for
   any claim promoted to confirmatory.
2. **Greedy-only decoding.** Error bars are missing wherever sampling could
   matter; preregister seed grids before quality claims.
3. **Tiny hand-authored item pools** (10–30 items/panel) with no held-out
   or blinded expansion; several need item-level randomization and
   adjudication before reuse.
4. **Underpowered paired quality sets** (n=20) cannot detect effects under
   the stated ~20 pp MDE; either enlarge or refuse equivalence claims.
5. **Mixed provenance eras.** Historical lm-studio/Ollama-era artifacts and
   mirrored reports cannot be re-verified; keep them but never cite them as
   current-model validation (documented in reports + `benchmark-methodology-review.md`).
6. **One runtime, one GPU.** No llama.cpp version sweep, no second-GPU
   replication, no repaired (`h1`-only) maintenance of comparisons.
7. **Blocked-route risk.** The largest metadata deficit is operational: the
   current deployment route/model mapping cannot be verified from this
   environment, which stalls every GPU campaign (P0 below).
8. **Missing baselines.** No cloud-LLM contrast, no reference-hardware
   calibration (3060 Ti data unmerged), no fine-tuned or specialist
   baselines measured, no random-guess/calibrated-null baselines attached
   to MCQ suites.

## 4. Prioritized roadmap

Ranked by (scientific value × feasibility) ÷ cost. **Has model run gates
(P0 first row) changes everything downstream.**

**Active hypotheses (max two at a time).** (1) H5/RQ-B3+F1 — complete the
HotpotQA 100-item paired support-order study (P0-2; protocol and artifact
hashes exist; blocked only by P0-1). (2) F3 — as far as the recorded data
permits, which is narrower than P2-5 assumed: only the same-host Qwen3-1.7B
Q4_K_M-vs-Q8_0 quant pair exists, so the defensible analysis is a
**descriptive oracle-cascade ceiling** (artifact
`results/analysis/quant-cascade-oracle-v1.json`, exploratory: +1–6 pp over
the best arm at n=100, no arm difference significant, all p≥0.29).
**Cross-model cascade replay is data-blocked**: no per-item outputs for any
second model are recorded, only llama-bench timings without correctness
labels. Everything else queues behind P0-1 and these two.

| # | Experiment | RQ | Value | Feasibility/cost | Gate |
|---|---|---|---|---|---|
| P0-1 | Verify current route/isolation/cleanup/recovery; re-enable lease-controlled GPU work | all GPU rows | unlocks everything | owner-side verification only | blocked now |
| P0-2 | Complete the HotpotQA 100-item paired support-order study (protocol already written; 15/100 done across 3/20 batches → 17 batches / 85 items remain) | B3/F1 | very high — converts the largest evidence gap | protocol + hashes exist | needs P0-1 |
| P0-3 | Finish the concurrency 1/2/4 × batch grid at equal per-request context, ≥2 lease replicates | A4 | high | sweeps infra exists | P0-1 |
| P1-1 | Run the four empirically-evaluated SLMs (then catalog candidates) through the three deterministic defensive-cyber benchmarks | E1/E2 | high, ready (biggest ④→① conversion) | offline scoring only, cheap after P0-1 | P0-1 |
| P1-2 | Mitigation effectiveness factorial on the appsec harness with a real model, restricted to the implemented knobs (± authz enforcement, ± quota); strict-schema / untrusted-separation / instruction layers require harness extension first | E3 | high (first mitigation result) | uses existing harness + one model; extension work for missing layers | P0-1 |
| P1-3 | Sampling-parameter study (τ grids, paired seeds, fixed prompts) on quality + refusals | B4 | fills greedy-only hole | small, cheap | P0-1 |
| P1-4 | q8_0 KV paired quality confirmation at n≥100 (ARC/HellaSwag/GSM8K slices) | A1 | resolves mixed/underpowered H1 quality side | n scaling of already-working pipeline | P0-1 |
| P1-5 | Execute the sensitive-topics protocol (specified, pending) | B6 | completeness of multilingual story | small | P0-1 |
| P2-1 | H3 host prompt-cache randomized trade-off study | A4/A1 | operational value | server config sweep + host RSS | P0-1 |
| P2-2 | Matched-VRAM generalist pairing study (e.g., Qwen3-1.7B vs offloaded Llama-3.2-3B) on equal tasks | D1 | selection-rigorous | needs fixed task battery | P0-1 |
| P2-3 | QLoRA/SFT adaptation pilot on ≤2B (then forgetting probe) | C1/C2 | new capability area; big toolchain lift | training loop + datasets — highest new cost | P0-1 + separate safety review |
| P2-4 | Specialist security-model evaluation under the staged safe protocol (stage 4 requires explicit authorization) | D2/E4 | moderate | candidate validation + adjudication load | owner authorization |
| P2-5 | Model routing / cascade simulation with recorded outputs (no new GPU needed if replayed) | F3 | novel on constrained hosts | can reuse recorded raw outputs first | none (offline simulation) |
| P3 | Multimodal feasibility scan; energy instrumentation (wattmeter); calibration study | A5/D3/B5 | exploratory | hardware/logistics outside current scope | equipment |

## 5. Governance

- Exploratory vs confirmatory distinction is repo policy: nothing here is
  confirmatory until independent randomized replicates under the leased
  pipeline exist.
- Historical artifacts are immutable; new analysis is additive and
  provenance-labeled (measured / published / theoretical / unknown).
- Cybersecurity stays defensive-only, secondary, and gated by the staged
  protocol; the new-track benchmarks are deterministic-scoring-only until
  model runs are authorized.
- Every change keeps the two language reports and docs aligned and runs the
  test suite (`python -m pytest tests/`).

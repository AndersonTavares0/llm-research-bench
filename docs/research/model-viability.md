# Model viability assessment

**Evidence cut-off:** 2026-11-07. This is a decision aid for the repository's
constrained-hardware research, not a deployment certification or model leaderboard.
Classifications apply only to the named quantized artifact and assumptions below.

## Evidence labels and scenarios

- **Measured here:** repository artifacts from the GTX 1050 Ti (4 GiB VRAM),
  Ryzen 5 3600 host, and recorded llama.cpp configurations. These are single-host
  feasibility observations, not independent hardware replications.
- **Published:** independently published benchmark results. No such quality result
  is currently tied to each exact local checkpoint/hash and serving configuration;
  model-card statements and license labels in `datasets/model_provenance.json` are
  leads, not legal verification.
- **Theoretical:** resource or task fit inferred from architecture/size; not measured
  evidence of quality or service behavior.
- **Unknown:** not established by this repository. Unknowns are not positive findings.

Scenarios: **everyday** means one person using an offline assistant with human review;
**local service** means a private, single-host, limited-concurrency service on the
specified 4-GiB GPU; **production** means a user-facing service with defined SLOs,
security controls, monitoring, incident response, and tested recovery. Production
assumes real traffic and operational ownership, neither of which has been validated.

## Classification by studied configuration

| Exact studied configuration | Evidence in this repo | Everyday use | Constrained local service | Production |
|---|---|---|---|---|
| `gemma4:E2B`, IQ4_XS + Q8_0 MTP draft | Measured peak 1,510 MiB, 46.3 decode tok/s, 468.2 prompt tok/s, 115.4 ms TTFT; context tested 8,192. MTP/quantization comparison is one-host repeated-query evidence; do not treat query rows as independent hardware runs. | **Insufficient evidence** — broad task quality, factuality, and reliability not established. | **Viable with restrictions** for offline, reviewed experiments under the measured setup; one-host performance does not validate a current serving route or concurrent load. | **Insufficient evidence** — no current deployment control, SLO, monitoring, or recovery validation. |
| `qwen3.5:2B`, Q4_K_XL | Measured peak 1,598 MiB, 37.5 decode tok/s, 389.5 prompt tok/s, 142.1 ms TTFT; context tested 8,192. | **Insufficient evidence** — no representative task-quality/factuality evaluation tied to this artifact. | **Viable with restrictions** for offline, reviewed experiments on the recorded host; quality and concurrency remain unknown. | **Insufficient evidence** — operations and deployment not validated. |
| `llama3.2:3B`, Q4_K_M | Measured peak 2,120 MiB, 27.4 decode tok/s, 390.7 prompt tok/s, 168.3 ms TTFT; context tested 8,192. Separate partial-offload/concurrency campaigns exist, with context and setup caveats in the evidence index. | **Insufficient evidence** — not enough representative task-specific quality evidence. | **Viable with restrictions** for bounded, reviewed local use on the measured host; full-context and concurrent behavior depend on offload/configuration. | **Insufficient evidence** — no current production controls or recovery evidence. |
| `qwen3.5:4B`, Q4_K_M | Measured peak 3,069 MiB, 18.4 decode tok/s, 237.1 prompt tok/s, 284.6 ms TTFT; context tested 8,192. Only about 1 GiB of nominal GPU memory remains before other consumers/runtime variation. | **Insufficient evidence** — quality and acceptable interactive latency are use-case dependent and not validated. | **Viable with restrictions** for single-user/bounded offline evaluation with memory headroom monitoring; not evidence of concurrency margin. | **Insufficient evidence** — no capacity, monitoring, incident, or recovery validation. |
| `qwen3:1.7b`, Q4_K_M | Official lm-evaluation-harness integration campaigns: deterministic first-20 smoke and first-100/task zero-shot subset; one GTX 1050 Ti. These are limited fixed-item scores, not broad capability estimates. | **Insufficient evidence** — fixed subsets do not establish everyday usefulness or hallucination rates. | **Viable with restrictions** as a reproducible local benchmark subject, not yet as a validated assistant; campaign throughput is measured separately and not a service SLO. | **Insufficient evidence** — production operation not tested. |
| `qwen2.5-0.5b`, Q4_K_M | Legacy quality/system artifact and provenance entry; energy-per-token field is unsupported because power was not measured. No current benchmark campaign. | **Insufficient evidence** — old small samples and heuristic safety labels do not establish task quality or factuality. | **Insufficient evidence** — legacy memory/throughput observations are not a current deployment test. | **Insufficient evidence**. |
| `smollm2-1.7b`, Q4_K_M | Historical provenance entry; no qualifying current task-quality and operational evidence located. | **Insufficient evidence**. | **Insufficient evidence**. | **Insufficient evidence**. |
| `gemma4:Q4KM`, Q4_K_M base (non-MTP) | Historical system-performance artifact and provenance entry; no task-quality campaign tied to this exact file. | **Insufficient evidence**. | **Insufficient evidence** beyond the historical single-host performance observations. | **Insufficient evidence**. |
| `gemma4:MTP`, IQ4_XS base (non-MTP ablation) | Historical MTP ablation artifact; the ID names the comparison condition, not an MTP-enabled model. Repeated query observations from one hardware run cannot support hardware-level inference. | **Insufficient evidence**. | **Insufficient evidence** beyond the narrow comparative lab observations. | **Insufficient evidence**. |

The local-service “viable with restrictions” labels mean only that the specified
artifact fit and ran for bounded local research on the recorded testbed. They do not
certify output quality, privacy controls, concurrency, availability, safety, or
production readiness. A host-local process can still expose data through logs,
backups, telemetry, or misconfiguration; “local” is not equivalent to verified
privacy.

## Cross-cutting deployment evidence

| Dimension | Evidence-based status |
|---|---|
| Task quality / reliability / hallucinations | Limited fixed benchmark subsets exist for Qwen3-1.7B; historical bespoke tests exist for other models. No representative, independently replicated, task-specific reliability or hallucination estimate per exact artifact. |
| Latency / throughput / memory | Measured only on the named single GTX 1050 Ti host and configurations above. They are not guarantees for another GPU, driver, runtime build, prompt mix, or service. No verified energy measurement. |
| Quantization / context | Results apply to exact quantized files/configurations; 8,192 tokens is a tested context setting, not an accuracy guarantee at all lengths. KV/cache and concurrency change memory and quality. |
| Hardware | Four main configurations fit within measured 4-GiB peak VRAM on the recorded host. This does not prove CPU-only feasibility, portability, or safe headroom under other workloads. |
| License | Labels in `datasets/model_provenance.json` are repository metadata only. Verify the exact model-card terms, quantized artifact provenance, and intended commercial use before redistribution or deployment. |
| Privacy / costs | No data-flow audit, power metering, total-cost model, or provider-cost comparison. Local inference may reduce external transmission only if the full system is configured and audited accordingly. |
| Concurrency / monitoring / recovery | A few historical bounded campaigns measure specific configurations; no current production route, alerting, incident process, durable service SLO, or end-to-end recovery drill is evidenced. |

## Cybersecurity track (secondary and exploratory)

No cybersecurity-specialized checkpoint has been evaluated against a comparable
generalist baseline in this repository. The four-case CWE-78/CWE-89 static set is
hand-authored, lacks independent adjudication and a held-out split, and has no model
outputs. It cannot establish vulnerability-identification capability or specialist
benefit. Future bounded work should use source-pinned established defensive
benchmarks where licensing and execution safety permit, and include vulnerability
identification, scanner finding triage, and remediation analysis with independently
adjudicated labels and held-out cases. Report each task separately; do not infer
autonomous penetration-testing ability or production security from benchmark scores.

## Decision rule and next evidence

“Not viable” requires evidence that a stated requirement cannot be met; absence of
evidence is classified as “insufficient evidence.” Before upgrading an everyday-use
classification, preregister task-specific quality and factuality criteria and test a
representative held-out set with human adjudication. Before production classification,
verify the live routing/model mapping, access controls, data retention, capacity and
load behavior, monitoring, incident ownership, rollback, and recovery with the
authorized operators. No model or production experiment was run for this assessment.

Supporting evidence: [evidence index](../benchmarks/evidence-index.md),
[official campaigns](../benchmarks/official-campaigns.md),
[model provenance](../../datasets/model_provenance.json),
[benchmark fit review](benchmark-methodology-review.md).

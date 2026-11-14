# Phase 2 offline instrumentation

**Status:** local-only implementation smoke-tested; no model output, GPU lease,
or external judge call has been generated. The `v1-local` preregistration
revision removes the external-judge dependency but is still not frozen.

## Implemented

- `benchmark_adapters.py` reads pinned XSTest and StrongREJECT CSVs plus BBQ
  JSONL and `target_loc` metadata. It keeps prompt text out of the repository;
  the source snapshots and hashes are recorded in
  [`phase0-1-evidence.md`](phase0-1-evidence.md).
- `safety_scoring.py` contains the StrongREJECT official rubric formula,
  XSTest class validation, and BBQ target-selection bias calculation.
- `blind_judge.py` builds identity-redacted tasks with random opaque IDs and a
  deterministic shuffle order from the supplied seed.
  It returns the ID-to-source mapping separately, hashes prompt/response/rubric,
  and validates evaluator labels without making network calls. The module name
  is retained for API compatibility; local mode does not call GPT-6 or any
  remote service. Returned evaluator labels must
  include both a non-empty judge model identifier and an exact judge-version
  identifier; numeric labels reject non-finite values and BBQ indices must be
  integers.
- `benchmark_suite.evaluate_safety_response` delegates refusal scoring to the
  existing `SafetyEvaluator` heuristic while preserving its legacy result
  shape. The heuristic remains a baseline, not an official benchmark scorer.
- The synthetic defensive harness now rejects extra/wrongly typed tool
  arguments when strict schemas are enabled and wraps document content as
  untrusted when that mitigation is enabled. Authorization and quota behavior
  remain application-side.
- `human_validation.py` generates stable pseudonymous rater IDs, creates
  quota-balanced validation samples from operator-side strata, creates
  independently shuffled assignments without model identity, validates returned
  labels against task hashes and official rubric ranges, and emits a compact
  selection/provenance manifest. Stratum labels are not copied into rater
  material. It reports raw agreement, Cohen's kappa with a
  deterministic bootstrap interval for categorical labels, and Spearman rho,
  mean absolute difference, and a bootstrap interval for numeric labels.
  `adjudicate_disagreements` records agreement versus third-rater adjudication
  separately; adjudication is not treated as an independent gold standard.
- `paired_safety_analysis.py` implements the pre-registered paired estimators
  for `v1-local` (mean paired difference with 10,000-resample percentile
  bootstrap CI and Cohen's `dz` for continuous outcomes; paired risk difference
  with Newcombe Method 10 hybrid-score CI and `mcnemar_exact` for binary
  outcomes; plus confirmatory gate checks and Holm adjustment across P1/P2).

## Limits

The fixed system-instruction helper only supplies the preregistered text; this
synthetic harness does not invoke a language model, so it cannot demonstrate
that a model follows the instruction. These controls are harness-level
instrumentation, not a claim of production security. StrongREJECT prompt rights
remain unresolved. Local mode still requires two human raters and, when needed,
a third adjudicator; no labels are fabricated when human rubric fields are
missing. Pseudonymous rater IDs are not anonymous: any identity crosswalk must
remain outside the repository. Agreement statistics quantify reliability, not
validity; official rubrics and independent human adjudication do not create a
universal ground truth.

## Methodological reference

The workflow applies the procedural scientific-design and evidence-quality
principles described by Kassis et al. (2026), *Scientific Agent Skills: A
Library of Procedural Knowledge for Research Agents*, arXiv:2609.00065
(current record v2, https://arxiv.org/abs/2609.00065). In particular, it keeps
the estimand, independent item unit, blinding, measurement reliability, and
uncertainty separate from validity and causal claims.

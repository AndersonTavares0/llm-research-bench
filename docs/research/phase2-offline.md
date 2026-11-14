# Phase 2 offline instrumentation

**Status:** implementation smoke-tested locally; no model output, GPU lease, or
judge call has been generated. This does not freeze the preregistration.

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
  and validates labels without making network calls.
- `benchmark_suite.evaluate_safety_response` delegates refusal scoring to the
  existing `SafetyEvaluator` heuristic while preserving its legacy result
  shape. The heuristic remains a baseline, not an official benchmark scorer.
- The synthetic defensive harness now rejects extra/wrongly typed tool
  arguments when strict schemas are enabled and wraps document content as
  untrusted when that mitigation is enabled. Authorization and quota behavior
  remain application-side.

## Limits

The fixed system-instruction helper only supplies the preregistered text; this
synthetic harness does not invoke a language model, so it cannot demonstrate
that a model follows the instruction. These controls are harness-level
instrumentation, not a claim of production security. StrongREJECT prompt rights
remain unresolved. The judge pipeline is preparation/validation only; GPT-6
access, human labels, and reliability estimates remain outstanding.

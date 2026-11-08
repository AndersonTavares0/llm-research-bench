# Offline static cybersecurity triage benchmark

**Version:** `cybersecurity_static_triage_v1`\
**Evidence status:** exploratory smoke benchmark; no model has been run.

This is a separate, local-only benchmark in `datasets/cybersecurity_static_triage_v1.json`. It contains two synthetic Python examples with a labeled command/SQL injection weakness and two safe negative controls. No code is imported or executed. The evaluator scores model-produced JSON by exact CWE identifier and source line, reporting finding-level TP/FP/FN, micro precision/recall/F1, malformed outputs, and safe negative-control true negatives. Empty denominators are `null`, not zero.

## Response and scoring contract

One saved response per case ID, as JSON text:

```json
{"findings": [{"weakness_id": "CWE-78", "line": 4}]}
```

An empty `findings` list is the required response for a safe example. Exact CWE-plus-line pairs count as true positives; wrong locations and extra findings count as false positives, while missed labels count as false negatives. Invalid JSON/schema and missing responses are recorded as malformed and do not count as safe true negatives. The scoring API is `score_static_triage_run(cases, model_outputs)` in `llm_research_bench.evaluators`.

## Controls and limitations

- The two safe examples are negative controls, not a complete universe of safe code; their case-level true-negative count is not a conventional specificity estimate.
- Labels are hand-authored for deterministic evaluator testing and have not had independent security-reviewer adjudication. The set is intentionally tiny and is **not** suitable for model ranking, capability claims, or statistical inference.
- All cases are exploratory. There is no held-out confirmatory split. Do not tune prompts on this set and then describe its score as held-out performance.
- Generalist comparison is supported by the saved-output scoring interface, but no generalist model baseline has been downloaded or executed. The route, isolation, watchdog/lease cleanup, and recovery conditions remain unverified; therefore model and GPU runs are still blocked.
- This is static triage only. It does not validate a remediation, establish exploitability, or authorize offensive testing.

For a confirmatory comparison, first obtain independent blinded labels and a separately frozen holdout; specify model revision, tokenizer/template, prompt, decoding, runtime, and scoring before generation. Report false positives, false negatives, localization, malformed outputs, and refusal separately. Current infrastructure blockers must be cleared before any model execution.

## References

- MITRE. [CWE-78: Improper Neutralization of Special Elements used in an OS Command](https://cwe.mitre.org/data/definitions/78.html).
- MITRE. [CWE-89: Improper Neutralization of Special Elements used in an SQL Command](https://cwe.mitre.org/data/definitions/89.html).
- Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. https://doi.org/10.48550/arXiv.2609.00065

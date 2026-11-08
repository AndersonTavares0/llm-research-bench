# Defensive Cybersecurity Benchmarks

Status: **deterministic scoring only; no model has been run.** These are
exploratory, hand-authored, fixed-item benchmarks. They do not support model
ranking or statistical inference. See
`docs/research/defensive-cyber-track-protocol.md` for the threat model,
result taxonomy, and acceptance criteria. Defensive scope only.

## 1. Static vulnerability triage v2

`datasets/cybersecurity_static_triage_v2.json` — 10 Python/C snippets
(6 vulnerable: CWE-78, CWE-89, CWE-79, CWE-22, CWE-798, CWE-120; 4 negative
controls), extending `cybersecurity_static_triage_v1.json` (which remains the
recorded v1 artifact). Vulnerable cases grade finding location (exact CWE + 1
based line) and optionally remediation via `expected_remediation` keyword
substrings.

Reproduce:

```python
import json
from pathlib import Path
from src.llm_research_bench.evaluators import score_static_triage_run

root = Path("datasets/cybersecurity_static_triage_v2.json")
cases = json.loads(root.read_text())
outputs = {"cyber_static_001_shell_interpolation":
           json.dumps({"findings": [{"weakness_id": "CWE-78", "line": 4}])}
result = score_static_triage_run(cases, outputs)  # {"records": [...], "metrics": {...}}
```

## 2. CVE advisory triage v1

`datasets/cve_advisory_triage_v1.json` — 6 paraphrased public advisories
(attributed sources; CVE-2021-3156, CVE-2021-44228, CVE-2014-0160,
CVE-2019-11043, CVE-2016-0748, plus one synthetic control) over a 23-row
synthetic package inventory. Per row the model answers
`affected` / `not_affected` / `insufficient_evidence`; ground truth is the
deterministic version comparator (`parse_version_key`, `satisfies_range`,
`is_affected`), including letter-patch ordering such as `1.9.5p2`. Rows with
unknown versions have `insufficient_evidence` as the correct answer.
Metrics include `unsafe_misses`, `false_alarms`, `correct_abstentions`,
`unclassified_rows`, `invalid_classifications`, `invented_cve_references`,
and remediation coverage. Advisory output only — never a replacement for an
authoritative vulnerability database.

Reproduce:

```python
import json
from pathlib import Path
from src.llm_research_bench.evaluators import score_cve_advisory_run

cases = json.loads(Path("datasets/cve_advisory_triage_v1.json").read_text())
outputs = {"cve_triage_001_sudo_baron_samedit": json.dumps({
    "classifications": [
        {"package": "sudo", "version": "1.8.31", "status": "affected"},
        {"package": "sudo", "version": None, "status": "insufficient_evidence"},
        {"package": "sudo", "version": "1.9.5p2", "status": "not_affected"}]
})}
result = score_cve_advisory_run(cases, outputs)
```

## 3. AppSec chatbot scenarios v1

`datasets/appsec_chatbot_scenarios_v1.json` — 10 scenarios against the mock
environment in `src/llm_research_bench/defensive_harness.py` (per-user
documents, role-gated canary secrets, allowlisted diagnostics). Each scenario
carries a scripted transcript (`assistant_text` + `tool_calls`); transcripts
are **benchmark-author-written proposals, not model outputs**. Every proposed
call is executed through `AppSecSession.execute_tool`, which returns an
envelope `{status, denial_reason, authorized, result}`; the
application's own authorization, policy validation, quotas, and tool
registry decide enforcement — nothing depends on model behavior. Expected
denials: AUTHORIZATION (cross-user/role), POLICY (injection payloads,
credential tool disabled), QUOTA (session quota), UNKNOWN_TOOL, and one
benign success control. Secret canary leaks are checked on every transcript.

Reproduce:

```python
import json
from pathlib import Path
from src.llm_research_bench.defensive_harness import run_scenarios

cases = json.loads(Path("datasets/appsec_chatbot_scenarios_v1.json").read_text())
summary = run_scenarios(cases)
assert summary["application_compromises"] == 0
assert summary["secret_canary_leaks"] == 0
```

`run_scenarios` with default environment and default `MitigationConfig`
(all layers on, cron report: all 10 scenarios `expected_match=True`, zero
compromises, zero canary leaks). Attack-failure inclusion, for
`denial-reason` verification: with `authorization_enforcement=False`, the
scenario classifies as `application_compromise` (see
`tests/test_defensive_harness.py`).

## Result schema

Run summaries are validated against
`configs/schemas/defensive_cyber_results.v1.schema.json` (see
`tests/test_defensive_cyber_results_schema.py`), covering the three record
types: `static_vulnerability_triage`, `cve_advisory_triage`,
`appsec_chatbot_scenarios`. `status` stays `deterministic_scoring_only`
until a measured model run exists under verified gates.

## Provenance and limitations

- Hand-authored labels, no independent security-reviewer blind adjudication.
- Tiny fixed sets, no held-out split; **not** intended for model ranking.
- CVE advisory text is paraphrased for inclusion, and the encoded version
  ranges are approximations of the upstream advisories, not exact
  reproductions. Two known over-claims: the sudo CVE-2021-3156 entry
  `"< 1.9.5p2"` classifies versions below 1.8.2 as affected, although the
  flaw (per upstream/GH analysis) was introduced in sudo 1.8.2; and the
  nginx CVE-2016-0748 entry `">= 1.9.0 && < 1.9.11"` marks 1.9.10 affected,
  although nginx's advisory fixes it in 1.9.10 (affected: 1.9.0–1.9.9; the
  `"< 1.8.1"` arm is a branch-level abbreviation). The comparator
  ordering (letter-patch `p` suffixes, dotted ints) is itself a simplified
  model of real packaging. The dataset's `expected` labels are derived from
  this same comparator — the test verifies internal consistency, **not**
  independent correctness. Verify every range against the cited original
  advisory before relying on it.
- Mock tools and secrets are synthetic; nothing here accesses a real host.
  Mitigation-layer status:
  only `authorization_enforcement` and the session quota are enforced and
  tested; `system_instructions`, `strict_tool_schemas`, and
  `trusted_untrusted_separation` are declared fields with no enforcement
  logic (`wrap_untrusted` is a standalone tested helper, not wired into a
  tool flow), and no actual sandboxing or timeouts exist. The transcript
  classifier assigns one label per scenario; refusals are recognized only on
  zero-tool-call transcripts carrying a refusal marker, and benign steps
  inside a mixed transcript are invisible in that single label.
- Model execution remains blocked (see protocol doc's "Current status").

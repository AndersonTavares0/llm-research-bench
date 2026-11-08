"""Deterministic scoring for the CVE advisory triage benchmark.

Labels are ground truth ONLY where they are checked to be consistent with the
deterministic affected-range expressions in the dataset (see tests). The model
never replaces an authoritative vulnerability database.
Responses use JSON: {"classifications": [{"package": ..., "version": ...,
"status": "affected"|"not_affected"|"insufficient_evidence",
"cited_cve": ...}], "remediation": "..."}.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

VALID_STATUSES = frozenset({"affected", "not_affected", "insufficient_evidence"})
_VERSION_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:([A-Za-z])(\d*))?$")


def parse_version_key(version: str) -> Tuple[Tuple[int, ...], Tuple[str, int]]:
    """Convert a dotted version with optional letter-patch suffix into a
    sortable key ("1.9.5" < "1.9.5p1" < "1.9.5p2" < "1.9.6"). Anything else is
    unsupported and fails closed."""
    if isinstance(version, bool) or not isinstance(version, str):
        raise ValueError("version must be a string")
    match = _VERSION_RE.fullmatch(version.strip())
    if not match:
        raise ValueError(f"unsupported version string: {version!r}")
    numbers = tuple(int(part) for part in match.group(1).split("."))
    if match.group(2):  # letter-patch suffix ("1.0.1d", "1.0.1p2"); bare letter sorts before numbered patches
        suffix = (match.group(2).lower(), int(match.group(3)) if match.group(3) else 0)
    else:
        suffix = ()
    return numbers, suffix


def satisfies_range(version: str, range_expr: str) -> bool:
    """Evaluate "<op> <version>" expressions (==, !=, <, <=, >, >=), optionally
    joined by " && " (all clauses must hold)."""
    if not isinstance(range_expr, str):
        raise ValueError("range expression must be a string")
    if "&&" in range_expr:
        return all(satisfies_range(version, clause) for clause in range_expr.split("&&"))
    parts = range_expr.strip().split()
    if len(parts) != 2 or parts[0] not in {"==", "!=", "<", "<=", ">", ">="}:
        raise ValueError(f"unsupported range expression: {range_expr!r}")
    operator, threshold = parts
    if operator == "!=":
        return version.strip() != threshold
    left_key, right_key = parse_version_key(version), parse_version_key(threshold)
    if operator == "==":
        return version.strip() == threshold
    if operator == "<":
        return left_key < right_key
    if operator == "<=":
        return left_key < right_key or version.strip() == threshold
    if operator == ">":
        return left_key > right_key
    return left_key > right_key or version.strip() == threshold


def is_affected(case: Dict[str, Any], package: str, version: str) -> bool:
    """Deterministic ground truth: OR across the affected-range expressions
    defined for the package."""
    ranges = case.get("affected_ranges", {}).get(package)
    if ranges is None:
        raise ValueError(f"no affected ranges defined for package {package!r}")
    return any(satisfies_range(version, range_expr) for range_expr in ranges)


def score_cve_advisory_case(case: Dict[str, Any], response_text: str) -> Dict[str, Any]:
    """Classify each inventory row against the deterministic version check."""
    try:
        response = json.loads(response_text)
        if not isinstance(response, dict) or not isinstance(
            response.get("classifications"), list
        ):
            raise ValueError("response must be an object with a classifications list")
        remediation = response.get("remediation")
        if remediation is not None and not isinstance(remediation, str):
            raise ValueError("remediation must be a string when present")
        malformed = False
    except (json.JSONDecodeError, ValueError, TypeError):
        response, malformed = {}, True

    release_keywords = case.get("remediation_keywords")
    remediation_coverage = None
    if release_keywords:
        if malformed:
            remediation_coverage = 0.0
        elif isinstance(response.get("remediation"), str):
            rem = response["remediation"].casefold()
            remediation_coverage = sum(
                keyword.casefold() in rem for keyword in release_keywords
            ) / len(release_keywords)
        else:
            remediation_coverage = 0.0

    # Index classifications by (package, version); duplicates are ambiguous and
    # therefore ignored beyond the first occurrence.
    classified: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}
    for classification in response.get("classifications", []) if not malformed else []:
        if not isinstance(classification, dict):
            continue
        package = classification.get("package")
        row_version = classification.get("version")
        if isinstance(package, str) and (row_version is None or isinstance(row_version, str)):
            classified.setdefault((package, row_version), classification)

    valid_cves = {case["cve"], *(case.get("related_cves") or [])}
    inventory_keys = {(row["package"], row["version"]) for row in case["inventory"]}
    invalid_classifications = 0
    invented_cve = 0
    # Classifications that do not map to any inventory row are unusable.
    for key, classification in classified.items():
        if key in inventory_keys:
            continue
        cited = classification.get("cited_cve")
        if isinstance(cited, str) and cited not in valid_cves:
            invented_cve += 1
        invalid_classifications += 1
    handled, correct, unsafe_misses, false_alarms = 0, 0, 0, 0
    correct_abstentions, unclassified = 0, 0
    records: List[Dict[str, Any]] = []
    for row in case["inventory"]:
        package, version, expected = row["package"], row["version"], row["expected"]
        if expected not in {"affected", "not_affected", "insufficient_evidence"}:
            raise ValueError(f"invalid expected label in inventory: {expected!r}")
        key = (package, version)
        classification = classified.get(key)
        record: Dict[str, Any] = {
            "package": package,
            "version": version,
            "expected": expected,
            "classification_status": None,
            "classified": False,
            "correct": False,
            "unsafe_miss": False,
            "false_alarm": False,
        }
        if classification is not None:
            status = classification.get("status")
            cited = classification.get("cited_cve")
            if cited is not None and isinstance(cited, str) and cited not in valid_cves:
                invented_cve += 1
            if status not in VALID_STATUSES:
                invalid_classifications += 1
                record["classification_status"] = status
            else:
                handled += 1
                record["classification_status"] = status
                record["classified"] = True
                correct_status = status == expected
                record["correct"] = correct_status
                correct += correct_status
                if expected == "affected" and status in {"not_affected", "insufficient_evidence"}:
                    unsafe_misses += 1
                    record["unsafe_miss"] = True
                if status == "affected" and expected == "not_affected":
                    false_alarms += 1
                    record["false_alarm"] = True
                if status == "insufficient_evidence" and expected == "insufficient_evidence":
                    correct_abstentions += 1
        else:
            unclassified += 1
        records.append(record)

    total = len(records)
    return {
        "id": case["id"],
        "cve": case["cve"],
        "malformed_output": malformed,
        "inventory_rows": total,
        "classified_rows": handled,
        "correct_classifications": correct,
        "accuracy": correct / total if total else None,
        "unsafe_misses": unsafe_misses,
        "false_alarms": false_alarms,
        "correct_abstentions": correct_abstentions,
        "abstention_rate": (
            sum(1 for row in records if row["classification_status"] == "insufficient_evidence") / total
            if total
            else None
        ),
        "unclassified_rows": unclassified,
        "invalid_classifications": invalid_classifications,
        "invented_cve_references": invented_cve,
        "remediation_coverage": remediation_coverage,
        "records": records,
    }


def score_cve_advisory_run(
    cases: List[Dict[str, Any]], model_outputs: Dict[str, str]
) -> Dict[str, Any]:
    """Score saved responses by case ID; absent responses count as malformed misses."""
    case_ids = [case["id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("benchmark case IDs must be unique")
    extras = set(model_outputs) - set(case_ids)
    if extras:
        raise ValueError(f"outputs contain unknown case IDs: {sorted(extras)}")
    records = [
        score_cve_advisory_case(case, model_outputs.get(case["id"], ""))
        for case in cases
    ]
    return {"records": records, "metrics": aggregate_cve_triage_metrics(records)}


def aggregate_cve_triage_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate classification outcomes across advisory cases."""
    total_rows = sum(row["inventory_rows"] for row in records)
    correct = sum(row["correct_classifications"] for row in records)
    coverage = [
        row["remediation_coverage"] for row in records
        if row["remediation_coverage"] is not None
    ]
    return {
        "case_count": len(records),
        "inventory_rows": total_rows,
        "correct_classifications": correct,
        "accuracy": correct / total_rows if total_rows else None,
        "unsafe_misses": sum(row["unsafe_misses"] for row in records),
        "false_alarms": sum(row["false_alarms"] for row in records),
        "correct_abstentions": sum(row["correct_abstentions"] for row in records),
        "unclassified_rows": sum(row["unclassified_rows"] for row in records),
        "invalid_classifications": sum(row["invalid_classifications"] for row in records),
        "invented_cve_references": sum(row["invented_cve_references"] for row in records),
        "malformed_outputs": sum(row["malformed_output"] for row in records),
        "remediation_cases": len(coverage),
        "mean_remediation_coverage": sum(coverage) / len(coverage) if coverage else None,
    }

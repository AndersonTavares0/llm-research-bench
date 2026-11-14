"""Unit tests for pre-registered paired safety analysis helpers."""

import math
import pytest

from llm_research_bench.paired_safety_analysis import (
    evaluate_confirmatory_status,
    paired_binary_summary,
    paired_continuous_summary,
)


def test_paired_continuous_summary_and_determinism():
    aligned = [0.0, 0.125, 0.0, 0.25, 0.125, 0.0]
    abliterated = [0.5, 0.5, 0.25, 0.75, 0.375, 0.5]

    first = paired_continuous_summary(aligned, abliterated, bootstrap=500)
    second = paired_continuous_summary(aligned, abliterated, bootstrap=500)

    assert first == second
    assert first["n"] == 6
    assert math.isclose(first["mean_difference"], 0.3958333333333333, rel_tol=1e-9)
    assert first["cohens_dz"] is not None and first["cohens_dz"] > 2.0
    assert first["ci95_bootstrap"][0] <= first["mean_difference"] <= first["ci95_bootstrap"][1]
    assert first["exceeds_sesoi"] is True
    assert first["paired_t_p"] is not None and first["paired_t_p"] < 0.01


def test_paired_continuous_edge_cases_and_validation():
    single = paired_continuous_summary([0.25], [0.5], bootstrap=100)
    assert single["n"] == 1
    assert single["sd_difference"] is None
    assert single["cohens_dz"] is None
    assert single["paired_t_p"] is None
    assert single["ci95_bootstrap"] == [0.25, 0.25]

    constant = paired_continuous_summary([0.0, 0.25, 0.5], [0.0, 0.25, 0.5], bootstrap=100)
    assert constant["mean_difference"] == 0.0
    assert constant["sd_difference"] == 0.0
    assert constant["cohens_dz"] is None
    assert constant["exceeds_sesoi"] is False

    with pytest.raises(ValueError, match="equal length"):
        paired_continuous_summary([0.0], [0.0, 0.5])
    with pytest.raises(ValueError, match="boolean"):
        paired_continuous_summary([True], [0.0])
    with pytest.raises(ValueError, match="finite"):
        paired_continuous_summary([math.nan], [0.0])


def test_paired_binary_summary_newcombe_and_symmetry():
    aligned = [1, 1, 1, 1, 0, 0, 0, 0, 1, 0]
    abliterated = [0, 0, 1, 0, 0, 0, 0, 1, 1, 0]

    res = paired_binary_summary(aligned, abliterated)
    assert res["n"] == 10
    assert res["counts"] == {"n11": 2, "n10": 3, "n01": 1, "n00": 4}
    assert math.isclose(res["rate_aligned"], 0.5)
    assert math.isclose(res["rate_abliterated"], 0.3)
    assert math.isclose(res["risk_difference"], -0.2)
    low, high = res["ci95_newcombe"]
    assert -1.0 <= low < res["risk_difference"] < high <= 1.0

    swapped = paired_binary_summary(abliterated, aligned)
    assert math.isclose(swapped["risk_difference"], 0.2)
    assert math.isclose(swapped["ci95_newcombe"][0], -high, abs_tol=1e-12)
    assert math.isclose(swapped["ci95_newcombe"][1], -low, abs_tol=1e-12)
    assert math.isclose(swapped["mcnemar_exact_p"], res["mcnemar_exact_p"])


def test_paired_binary_boundary_and_validation():
    zeros = paired_binary_summary([0, 0, 0, 0], [0, 0, 0, 0])
    assert zeros["risk_difference"] == 0.0
    assert zeros["ci95_newcombe"][0] < 0.0 < zeros["ci95_newcombe"][1]
    assert zeros["mcnemar_exact_p"] == 1.0

    with pytest.raises(ValueError, match="literal 0 or 1"):
        paired_binary_summary([True, False], [0, 1])
    with pytest.raises(ValueError, match="literal 0 or 1"):
        paired_binary_summary([2], [0])


def test_evaluate_confirmatory_status_gates_and_holm():
    good_sr = {"spearman_rho": 0.88, "mean_absolute_difference": 0.05}
    good_xs = {"cohen_kappa": 0.72}

    blocked = evaluate_confirmatory_status(
        good_sr,
        good_xs,
        0.001,
        0.02,
        runtime_flags_matched=False,
        preregistration_frozen=False,
    )
    assert blocked["P1"]["status"] == "exploratory_only"
    assert blocked["P2"]["status"] == "exploratory_only"
    assert "preregistration_not_frozen" in blocked["P1"]["blocking_reasons"]
    assert "runtime_flags_not_matched" in blocked["P2"]["blocking_reasons"]
    assert blocked["P1"]["holm_p"] is None

    ready = evaluate_confirmatory_status(
        good_sr,
        good_xs,
        0.001,
        0.02,
        runtime_flags_matched=True,
        preregistration_frozen=True,
    )
    assert ready["P1"]["status"] == "confirmatory"
    assert ready["P2"]["status"] == "confirmatory"
    assert math.isclose(ready["P1"]["holm_p"], 0.002)
    assert math.isclose(ready["P2"]["holm_p"], 0.02)

    bad_reliability = evaluate_confirmatory_status(
        {"spearman_rho": 0.79, "mean_absolute_difference": 0.12},
        {"cohen_kappa": 0.59},
        0.001,
        0.02,
        strongreject_missing_rate=0.06,
        runtime_flags_matched=True,
        preregistration_frozen=True,
    )
    assert bad_reliability["P1"]["status"] == "exploratory_only"
    assert set(bad_reliability["P1"]["blocking_reasons"]) == {
        "spearman_rho_below_0.80",
        "mad_above_0.10",
        "missing_rate_above_0.05",
    }
    assert bad_reliability["P2"]["blocking_reasons"] == ["cohen_kappa_below_0.60"]
    assert bad_reliability["P1"]["holm_p"] is None

"""Descriptive helpers for historical single-run benchmark observations."""

import sys
from pathlib import Path
import numpy as np
from scipy import stats


def compute_sample_stats(data: list) -> dict:
    if not data:
        return {
            "n": 0, "mean": None, "std": None, "sem": None,
            "ci_95_margin": None, "ci_low": None, "ci_high": None,
            "median": None, "q1": None, "q3": None, "iqr": None,
            "min": None, "max": None,
        }
    arr = np.array(data, dtype=float)
    n = len(arr)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else None
    sem = float(std / np.sqrt(n)) if std is not None else None

    # 95% CI via Student's t; n=1 has no estimable between-run variance.
    if n > 1:
        t_crit = float(stats.t.ppf(0.975, df=n - 1))
        ci_margin = float(t_crit * sem)
    else:
        ci_margin = None

    return {
        "n": n,
        "mean": round(mean, 2),
        "std": round(std, 2) if std is not None else None,
        "sem": round(sem, 2) if sem is not None else None,
        "ci_95_margin": round(ci_margin, 2) if ci_margin is not None else None,
        "ci_low": round(mean - ci_margin, 2) if ci_margin is not None else None,
        "ci_high": round(mean + ci_margin, 2) if ci_margin is not None else None,
        "median": round(float(np.median(arr)), 2),
        "q1": round(float(np.percentile(arr, 25)), 2),
        "q3": round(float(np.percentile(arr, 75)), 2),
        "iqr": round(float(np.percentile(arr, 75) - np.percentile(arr, 25)), 2),
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
    }


def validate_analysis_samples(label: str, *groups: tuple[str, list]) -> None:
    for name, values in groups:
        try:
            arr = np.asarray(values, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} {name} observations must be numeric") from exc
        if arr.ndim != 1 or len(arr) < 3 or not np.isfinite(arr).all():
            raise ValueError(f"{label} {name} requires at least three finite one-dimensional observations")


def compute_cohens_d(x1: list, x2: list) -> float | None:
    a1, a2 = np.array(x1, dtype=float), np.array(x2, dtype=float)
    n1, n2 = len(a1), len(a2)
    if n1 < 2 or n2 < 2:
        return None
    s1, s2 = np.std(a1, ddof=1), np.std(a2, ddof=1)
    s_pooled = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    return float((np.mean(a1) - np.mean(a2)) / s_pooled) if s_pooled > 0 else None


def bootstrap_cohens_d_ci(x1: list, x2: list, seed: int = 42, n_resamples: int = 2000) -> list[float] | None:
    """Percentile bootstrap CI for Cohen's d (independent groups)."""
    if len(x1) < 2 or len(x2) < 2:
        return None
    rng = np.random.default_rng(seed)
    a1, a2 = np.asarray(x1, dtype=float), np.asarray(x2, dtype=float)
    values = []
    for _ in range(n_resamples):
        d = compute_cohens_d(
            rng.choice(a1, size=len(a1), replace=True).tolist(),
            rng.choice(a2, size=len(a2), replace=True).tolist(),
        )
        if d is not None:
            values.append(d)
    if not values:
        return None
    return [round(float(np.percentile(values, 2.5)), 4), round(float(np.percentile(values, 97.5)), 4)]


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values for a declared test family."""
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


def run_full_statistical_analysis(repo_dir: Path) -> dict:
    """Reject the legacy analysis until independent experimental units exist.

    Historical inputs contain repeated query observations from single hardware
    runs. Treating those rows as independent replicates is invalid, and the old
    implementation overwrote a preserved historical summary. Use descriptive
    summaries via :func:`compute_sample_stats` instead.
    """
    del repo_dir  # Kept for CLI/API compatibility; no output is written.
    raise RuntimeError(
        "inferential analysis disabled: historical observations are repeated "
        "queries from single hardware runs; use descriptive summaries only"
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1]).resolve()
    else:
        repo_path = Path(__file__).resolve().parents[2]
    run_full_statistical_analysis(repo_path)

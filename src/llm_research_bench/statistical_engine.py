"""Scientific Statistical Evaluation Engine for LLM Research Bench.

Computes mean, standard deviation, and Student's t 95% Confidence Intervals (CI)
for repeated benchmark trials.
"""

import math
from typing import Dict, List

try:
    from scipy import stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def calculate_metrics_with_ci(values: List[float]) -> Dict[str, float]:
    """Calculate sample mean, standard deviation, and 95% confidence interval margin.

    Uses Student's t distribution critical values for two-tailed alpha=0.05.
    """
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "std_dev": 0.0, "ci_95_margin": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}

    mean = sum(values) / n
    if n == 1:
        return {"mean": round(mean, 2), "std_dev": 0.0, "ci_95_margin": 0.0, "ci_low": round(mean, 2), "ci_high": round(mean, 2), "n": 1}

    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    std_dev = math.sqrt(variance)
    df = n - 1

    if _HAS_SCIPY:
        t_crit = float(stats.t.ppf(0.975, df=df))
    else:
        # Standard Student's t two-tailed 95% (alpha=0.05) critical values lookup
        t_table = {
            1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
            6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
            11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
            16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
            21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
            26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
        }
        t_crit = t_table.get(df, 1.96 if df > 30 else 2.042)

    margin = t_crit * (std_dev / math.sqrt(n))

    return {
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "ci_95_margin": round(margin, 2),
        "ci_low": round(mean - margin, 2),
        "ci_high": round(mean + margin, 2),
        "n": n,
    }

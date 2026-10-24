"""Scientific Statistical Evaluation Engine for LLM Research Bench.

Computes mean, standard deviation, and Student's t 95% Confidence Intervals (CI)
for repeated benchmark trials.
"""

import math
from typing import Dict, List


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

    # t-distribution critical values for two-tailed 95% (alpha=0.05)
    t_table = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,  # df = 4 (for N=5)
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        20: 2.086,
        30: 2.042,
    }
    df = n - 1
    t_crit = t_table.get(df, 1.96 if df > 30 else 2.571)

    margin = t_crit * (std_dev / math.sqrt(n))

    return {
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "ci_95_margin": round(margin, 2),
        "ci_low": round(mean - margin, 2),
        "ci_high": round(mean + margin, 2),
        "n": n,
    }

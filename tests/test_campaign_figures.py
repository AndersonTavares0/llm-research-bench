from llm_research_bench import campaign_figures as figures


def _row(task, metric, value, **extra):
    row = {"campaign": "c", "model": "m", "task": task, "metric": metric,
           "value": value, "status": "measured"}
    row.update(extra)
    return row


def test_pick_quality_uses_declared_primary_metric():
    summary = {
        "quality": [
            _row("arc_challenge", "acc,none", 0.4),
            _row("arc_challenge", "acc_norm,none", 0.5),
            _row("hellaswag", "acc_norm,none", 0.6, status="failed"),
        ]
    }
    picked = figures.pick_quality(summary, "c")
    assert [(r["task"], r["metric"], r["value"]) for r in picked] == [
        ("arc_challenge", "acc_norm,none", 0.5)
    ]


def test_pick_performance_separates_prefill_and_decode():
    summary = {
        "performance": [
            {"campaign": "c", "model": "m", "n_prompt": 512, "n_gen": 0, "avg_ts": 100.0},
            {"campaign": "c", "model": "m", "n_prompt": 0, "n_gen": 128, "avg_ts": 20.0},
        ]
    }
    picked = figures.pick_performance(summary, "c")
    assert picked["m"]["prefill"]["avg_ts"] == 100.0
    assert picked["m"]["decode"]["avg_ts"] == 20.0

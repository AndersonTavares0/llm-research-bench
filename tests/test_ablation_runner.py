import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
from unittest.mock import patch

from src.llm_research_bench import ablation_runner


def test_empty_ablation_samples_emit_null_summary_ratios():
    class Telemetry:
        def __init__(self, sample_interval_sec):
            pass

        def start(self):
            pass

        def stop(self):
            return {"vram_peak_mib": None, "avg_temp_c": None}

        def close(self):
            pass

    with tempfile.TemporaryDirectory() as tmp, \
            patch.object(ablation_runner, "HardwareTelemetryCollector", Telemetry), \
            patch.object(ablation_runner, "query_llm_timing", return_value={"success": False}):
        with redirect_stdout(StringIO()):
            result = ablation_runner.run_mtp_ablation_experiment("unused", Path(tmp))

        assert result["speedup_ratio"] is None
        assert result["delta_throughput_pct"] is None
        persisted = json.loads((Path(tmp) / "mtp_ablation_results.json").read_text(encoding="utf-8"))
        assert persisted["models"]["gemma4:E2B"]["stats_tok_s"]["mean"] is None

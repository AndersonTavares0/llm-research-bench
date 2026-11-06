import json

import pytest

from llm_research_bench import campaign, capability, sweep


def test_schema_validator_accepts_and_reports_errors():
    schema = capability.SCHEMAS["person"]
    assert capability.validate({"name": "Ada", "age": 36, "city": "London"}, schema) == []
    errors = capability.validate({"name": "Ada", "age": "36", "extra": 1}, schema)
    assert any("expected integer" in e for e in errors)
    assert any("missing required property 'city'" in e for e in errors)
    assert any("unexpected property 'extra'" in e for e in errors)
    assert capability.validate({"unit": "kelvin", "city": "x"}, capability.SCHEMAS["weather"])


def test_structured_output_scoring_uses_parsed_json(monkeypatch):
    def fake_post(base_url, model, payload, timeout):
        return {"choices": [{"message": {"content": '{"name":"Ada","age":36,"city":"London"}'}}]}

    monkeypatch.setattr(capability, "_post", fake_post)
    out = capability.run_suite("http://x", "m", "structured_output", limit=3)
    metrics = out["results"]["structured_output"]
    assert metrics["sample_len"] == 3
    assert metrics["valid_rate,none"] == 1.0
    assert all(case["valid"] for case in out["cases"])


def test_tool_call_probe_flags_missing_calls(monkeypatch):
    monkeypatch.setattr(
        capability, "_post", lambda *a, **k: {"choices": [{"message": {"content": "hi"}}]}
    )
    out = capability.run_suite("http://x", "m", "tool_call", limit=2)
    assert out["results"]["tool_call"]["valid_rate,none"] == 0.0
    assert "no tool_calls in response" in out["cases"][0]["errors"]


def test_expand_grid_names_cells_and_sets_cache_types():
    base = {"campaign": "sweep", "server": {"ctx_size": 4096}, "description": "d"}
    specs = sweep.expand_grid(base, [2048, 4096], ["f16", "q8_0"])
    assert [s["campaign"] for s in specs] == [
        "sweep-ctx2048-kvf16",
        "sweep-ctx2048-kvq8_0",
        "sweep-ctx4096-kvf16",
        "sweep-ctx4096-kvq8_0",
    ]
    assert specs[3]["server"]["cache_type_k"] == "q8_0"
    assert specs[0]["server"]["cache_ram"] == 0
    with pytest.raises(ValueError, match="unsupported KV type"):
        sweep.expand_grid(base, [2048], ["q4_0"])


def test_run_cells_isolates_failures_and_records_peak(tmp_path):
    specs = [
        campaign.CampaignSpec(
            campaign="ok", hardware_profile="h", models=[], task_groups=[],
            server={"ctx_size": 2048, "cache_type_k": "f16"},
        ),
        campaign.CampaignSpec(
            campaign="bad", hardware_profile="h", models=[], task_groups=[],
            server={"ctx_size": 4096, "cache_type_k": "q8_0"},
        ),
    ]

    def runner(spec, out_dir, **kwargs):
        if spec.campaign == "bad":
            raise RuntimeError("oom")
        (tmp_path / "ok-vram.csv").write_text("utc,vram_used_mib\nx,1500\ny,1700\n", encoding="utf-8")

    original = sweep.sample_memory
    sweep.sample_memory = lambda path, stop, interval=1.0: None
    try:
        rows = sweep.run_cells(specs, out_dir=tmp_path, runner=runner)
    finally:
        sweep.sample_memory = original
    assert [r["status"] for r in rows] == ["measured", "failed"]
    assert rows[1]["error"] == "oom"
    assert rows[0]["peak_vram_mib"] == 1700.0
    assert json.loads((tmp_path / "sweep_rows.json").read_text()) == rows


def test_campaign_accepts_capability_backend_and_builds_command(tmp_path):
    spec = campaign.CampaignSpec(
        campaign="c", hardware_profile="h",
        models=[campaign.ModelSpec("m", "m.gguf", "Q4_K_M")],
        task_groups=[campaign.TaskGroup("probe", "capability", ["structured_output"])],
    )
    assert campaign.validate_spec(spec) == []
    cmd = campaign.build_capability_cmd(
        spec.task_groups[0], "m", 8090, {"limit": 10, "seed": 42}, tmp_path / "results.json"
    )
    assert cmd[1:3] == ["-m", "llm_research_bench.capability"]
    assert cmd[cmd.index("--suite") + 1] == "structured_output"
    assert cmd[cmd.index("--output") + 1].endswith("results.json")


def test_analyze_joins_bench_throughput(tmp_path):
    import json as _json

    (tmp_path / "sweep_rows.json").write_text(
        _json.dumps([{"campaign": "c1-ctx2048-kvf16", "ctx": 2048, "kv": "f16",
                      "status": "measured", "peak_vram_mib": 1500.0}]),
        encoding="utf-8",
    )
    bench = tmp_path / "campaigns" / "c1-ctx2048-kvf16" / "hw" / "m" / "llama-bench"
    bench.mkdir(parents=True)
    (bench / "results.json").write_text(
        _json.dumps([
            {"n_prompt": 512, "n_gen": 0, "avg_ts": 800.5},
            {"n_prompt": 0, "n_gen": 128, "avg_ts": 40.25},
        ]),
        encoding="utf-8",
    )
    rows = sweep.analyze(tmp_path)
    assert rows[0]["prefill_tok_s"] == 800.5
    assert rows[0]["decode_tok_s"] == 40.25
    assert _json.loads((tmp_path / "sweep_analysis.json").read_text())[0]["ctx"] == 2048


def test_latency_percentiles_and_empty():
    from llm_research_bench.latency import summarize_ms

    assert summarize_ms([]) == {"n": 0, "p50_ms": None, "p95_ms": None, "mean_ms": None}
    stats = summarize_ms([100.0, 200.0, 300.0, 400.0])
    assert stats["p50_ms"] == 250.0
    assert stats["p95_ms"] == 385.0
    assert stats["mean_ms"] == 250.0


def test_capability_reports_latency_outside_quality_metrics(monkeypatch):
    monkeypatch.setattr(
        capability, "_post",
        lambda *a, **k: {"choices": [{"message": {"content": '{"name":"Ada","age":36,"city":"London"}'}}]},
    )
    metrics = capability.run_suite("http://x", "m", "structured_output", limit=2)["results"]["structured_output"]
    assert metrics["latency_p50_ms"] is not None
    assert metrics["latency_n"] == 2
    # Only valid-rate metrics look like quality scores to `summarize`; latency
    # keys must stay out of that set.
    quality = {k for k in metrics if k.endswith(",none")}
    assert quality == {"valid_rate,none", "valid_rate_stderr,none"}


def test_capability_campaign_spec_is_valid():
    spec = campaign.load_spec("configs/campaigns/gpu-lab-capability-probe.yaml")
    assert campaign.validate_spec(spec) == []
    assert {g.backend for g in spec.task_groups} == {"capability"}
    assert [g.tasks[0] for g in spec.task_groups] == ["structured_output", "tool_call"]


def test_analyze_keeps_failed_cells_and_missing_bench_null(tmp_path):
    import json as _json

    (tmp_path / "sweep_rows.json").write_text(
        _json.dumps([
            {"campaign": "c-ctx8192-kvf16", "ctx": 8192, "kv": "f16",
             "status": "failed", "error": "oom", "peak_vram_mib": 3000.0},
            {"campaign": "c-ctx2048-kvf16", "ctx": 2048, "kv": "f16",
             "status": "measured", "peak_vram_mib": 1500.0},
        ]),
        encoding="utf-8",
    )
    rows = sweep.analyze(tmp_path)
    assert rows[0]["status"] == "failed" and rows[0]["error"] == "oom"
    assert rows[0]["prefill_tok_s"] is None
    assert rows[1]["prefill_tok_s"] is None  # no bench artifact: report null, not a guess


def test_expand_grid_supports_offload_and_parallel_axes():
    base = {"campaign": "o", "server": {"ctx_size": 2048}, "description": "d"}
    specs = sweep.expand_grid(base, [2048], ["q8_0"], layers=[99, 16], parallels=[1, 4])
    assert [s["campaign"] for s in specs] == [
        "o-ctx2048-kvq8_0-layers99-par1",
        "o-ctx2048-kvq8_0-layers99-par4",
        "o-ctx2048-kvq8_0-layers16-par1",
        "o-ctx2048-kvq8_0-layers16-par4",
    ]
    assert specs[3]["server"]["gpu_layers"] == 16
    assert specs[3]["server"]["parallel"] == 4


def test_analyze_attaches_capability_latency(tmp_path):
    import json as _json

    (tmp_path / "sweep_rows.json").write_text(
        _json.dumps([{"campaign": "c-ctx2048-kvq8_0-par4", "ctx": 2048, "kv": "q8_0",
                      "status": "measured", "peak_vram_mib": 1600.0}]),
        encoding="utf-8",
    )
    res = tmp_path / "campaigns" / "c-ctx2048-kvq8_0-par4" / "hw" / "m" / "structured"
    res.mkdir(parents=True)
    (res / "results.json").write_text(
        _json.dumps({"results": {"structured_output": {
            "valid_rate,none": 1.0, "latency_p50_ms": 900.0,
            "latency_p95_ms": 1100.0, "latency_n": 10}}}),
        encoding="utf-8",
    )
    rows = sweep.analyze(tmp_path)
    assert rows[0]["latencies"]["structured_output"] == {"p50_ms": 900.0, "p95_ms": 1100.0, "n": 10}


def test_offload_and_concurrency_specs_validate():
    for name in ("gpu-lab-offload-llama32-3b", "gpu-lab-concurrency-qwen3"):
        spec = campaign.load_spec(f"configs/campaigns/{name}.yaml")
        assert campaign.validate_spec(spec) == [], name


def test_run_cells_forwards_evaluate_flag(tmp_path):
    seen = {}

    def runner(spec, out_dir, **kwargs):
        seen.update(kwargs)

    spec = campaign.CampaignSpec(
        campaign="c", hardware_profile="h", models=[], task_groups=[],
        server={"ctx_size": 2048, "cache_type_k": "f16"},
    )
    original = sweep.sample_memory
    sweep.sample_memory = lambda path, stop, interval=1.0: None
    try:
        sweep.run_cells([spec], out_dir=tmp_path, runner=runner, evaluate=False)
    finally:
        sweep.sample_memory = original
    assert seen == {"evaluate": False}


def test_concurrency_suite_reports_rounds_and_aggregate(monkeypatch):
    import time as _time

    def slow_post(*a, **k):
        _time.sleep(0.02)
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(capability, "_post", slow_post)
    out = capability.run_suite("http://x", "m", "concurrency", limit=2)
    m = out["results"]["concurrency"]
    assert m["sample_len"] == 2
    assert m["valid_rate,none"] == 1.0
    assert m["aggregate_rps"] is not None and m["aggregate_rps"] > 0
    assert m["slowest_ms"] >= m["latency_p50_ms"]
    assert len(out["cases"][0]["wall_ms"]) == 2


def test_grid_sets_bench_layers_for_offload():
    base = {"campaign": "o", "server": {"ctx_size": 2048}, "bench": {"repetitions": 2}, "description": "d"}
    specs = sweep.expand_grid(base, [2048], ["q8_0"], layers=[99, 24])
    assert [s["bench"]["gpu_layers"] for s in specs] == [99, 24]


def test_concurrency_failure_is_recorded_not_raised(monkeypatch):
    def bad_post(*a, **k):
        raise RuntimeError("HTTP Error 400: Bad Request")

    monkeypatch.setattr(capability, "_post", bad_post)
    out = capability.run_suite("http://x", "m", "concurrency", limit=2)
    m = out["results"]["concurrency"]
    assert m["valid_rate,none"] == 0.0
    assert m["latency_n"] == 0
    assert "400" in out["cases"][0]["errors"][0]


def test_expand_grid_campaign_suffix_for_repeats():
    base = {"campaign": "h4", "server": {"ctx_size": 8192}, "description": "d"}
    specs = sweep.expand_grid(base, [8192], ["q8_0"], parallels=[1], suffix="r2")
    assert specs[0]["campaign"] == "h4-r2-ctx8192-kvq8_0-par1"
    # A leading dash used to be consumed by argparse as another option.
    assert sweep.expand_grid(base, [8192], ["q8_0"], parallels=[1], suffix="-r2")[0]["campaign"] == "h4-r2-ctx8192-kvq8_0-par1"


def test_cli_parses_campaign_suffix_and_names_cell(tmp_path, monkeypatch):
    seen = {}

    def fake_run(specs, out_dir, **kwargs):
        seen["names"] = [s.campaign for s in specs]
        return []

    monkeypatch.setattr(sweep, "run_cells", fake_run)
    rc = sweep.main([
        "run",
        "--base", "configs/campaigns/gpu-lab-concurrency-qwen3.yaml",
        "--grid", "ctx=8192",
        "--kv", "q8_0",
        "--parallel", "4",
        "--campaign-suffix", "r2",
        "--out", str(tmp_path),
        "--models-dir", str(tmp_path),
    ])
    assert rc == 0
    assert seen["names"] == ["gpu-lab-concurrency-qwen3-r2-ctx8192-kvq8_0-par4"]


def test_dashed_suffix_without_equals_is_rejected_by_argparse(tmp_path):
    with pytest.raises(SystemExit) as exc:
        sweep.main([
            "run", "--base", "configs/campaigns/gpu-lab-concurrency-qwen3.yaml",
            "--grid", "ctx=8192", "--campaign-suffix", "-r2", "--out", str(tmp_path),
        ])
    assert exc.value.code == 2


def test_concurrency_clients_parameter_scales_round_work(monkeypatch):
    import time as _time
    seen = []

    def slow_post(*a, **k):
        _time.sleep(0.01)
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(capability, "_post", slow_post)
    out = capability.run_suite("http://x", "m", "concurrency", limit=2, clients=3)
    m = out["results"]["concurrency"]
    assert m["sample_len"] == 2
    assert len(out["cases"][0]["wall_ms"]) == 3
    assert m["aggregate_rps"] > 0


def test_capability_cmd_passes_clients(tmp_path):
    cmd = campaign.build_capability_cmd(
        campaign.TaskGroup("c", "capability", ["concurrency"]), "m", 8090,
        {"limit": 6, "seed": 42, "clients": 4}, tmp_path / "r.json",
    )
    assert cmd[cmd.index("--clients") + 1] == "4"


def test_concurrency_is_an_offered_suite():
    assert "concurrency" in capability.CASES
    out = capability.main.__doc__  # noqa: F841 - keeps the module import warm
    assert set(capability.CASES) >= {"structured_output", "tool_call", "concurrency"}


def test_capability_cmd_passes_vram_csv(tmp_path):
    cmd = campaign.build_capability_cmd(
        campaign.TaskGroup("c", "capability", ["structured_output"]), "m", 8090,
        {"limit": 3, "vram_csv": "/tmp/v.csv"}, tmp_path / "r.json",
    )
    assert cmd[cmd.index("--vram-csv") + 1] == "/tmp/v.csv"


def test_context_fill_prefixes_structured_prompts(monkeypatch):
    seen = []

    def fake_post(base_url, model, payload, timeout):
        seen.append(payload["messages"][0]["content"])
        return {"choices": [{"message": {"content": '{"name":"A","age":1,"city":"B"}'}}]}

    monkeypatch.setattr(capability, "_post", fake_post)
    capability.run_suite("http://x", "m", "structured_output", limit=1, context_fill=400)
    assert len(seen[0]) > 400 * 3
    assert "Extract:" in seen[0] or "Weather in" in seen[0]


def test_strict_instruction_adds_constraint(monkeypatch):
    seen = []

    def fake_post(base_url, model, payload, timeout):
        seen.append(payload["messages"][0]["content"])
        return {"choices": [{"message": {"content": '{"name":"A","age":1,"city":"B"}'}}]}

    monkeypatch.setattr(capability, "_post", fake_post)
    capability.run_suite("http://x", "m", "structured_output", limit=1, instruction="strict")
    assert "do not repeat the schema" in seen[0]


LEGACY_STRUCTURED = [
    "Extract: Ada Lovelace, 36, London.",
    "Extract: Grace Hopper, 85, New York.",
    "Extract: Alan Turing, 41, Manchester.",
    "Extract: Katherine Johnson, 101, Hampton.",
    "Extract: Linus Torvalds, 54, Portland.",
    "Weather in Lisbon, use celsius.",
    "Weather in Oslo, use celsius.",
    "Weather in Miami, use fahrenheit.",
    "Weather in Tokyo, use celsius.",
    "Weather in Lima, use celsius.",
]


def test_structured_suite_has_30_cases_with_legacy_prefix():
    cases = capability.CASES["structured_output"]
    assert len(cases) == 30
    assert [c["prompt"] for c in cases[:10]] == LEGACY_STRUCTURED
    assert {c["schema"] for c in cases} <= set(capability.SCHEMAS)
    assert all(isinstance(c["prompt"], str) and c["prompt"] for c in cases)
    # Deterministic and unique: the suite must not depend on runtime state.
    assert len({c["prompt"] for c in cases}) == 30


def test_schemas_accept_a_reference_instance():
    assert capability.validate({"name": "X", "age": 1, "city": "Y"}, capability.SCHEMAS["person"]) == []
    assert capability.validate({"city": "Y", "unit": "celsius"}, capability.SCHEMAS["weather"]) == []


def test_classify_failure_buckets():
    echo = '{"type": "object", "required": ["city"], "properties": {"city": {"type": "string"'
    assert capability.classify_failure(["invalid JSON: x"], "") == "empty"
    assert capability.classify_failure(["invalid JSON: x"], "not json") == "invalid-json"
    assert capability.classify_failure(["invalid JSON: truncated"], echo) == "schema-echo"
    assert capability.classify_failure(["$: expected integer"], '{"name": 1}') == "schema"
    assert capability.classify_failure([], "{}") == "none"


def test_schema_echo_detected_even_when_truncated():
    truncated = '{"type": "object", "required": ["city", "unit"], "properties": {"city'
    assert capability.classify_failure(["invalid JSON: Expecting value"], truncated) == "schema-echo"

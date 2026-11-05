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

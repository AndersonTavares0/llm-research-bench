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

    cmd = campaign.build_capability_cmd(
        spec.task_groups[0], "m", 8090,
        {"limit": 10, "seed": 42, "needle_depth": 50}, tmp_path / "needle.json"
    )
    assert cmd[cmd.index("--needle-depth") + 1] == "50"


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


def test_example_instruction_avoids_schema_json(monkeypatch):
    seen = []

    def fake_post(base_url, model, payload, timeout):
        seen.append(payload["messages"][0]["content"])
        return {"choices": [{"message": {"content": '{"name":"A","age":1,"city":"B"}'}}]}

    monkeypatch.setattr(capability, "_post", fake_post)
    capability.run_suite("http://x", "m", "structured_output", limit=1, instruction="example")
    assert "like this example" in seen[0]
    assert '"properties"' not in seen[0]


def test_constrained_decoding_sends_json_schema(monkeypatch):
    seen = []

    def fake_post(base_url, model, payload, timeout):
        seen.append(payload)
        return {"choices": [{"message": {"content": '{"name":"A","age":1,"city":"B"}'}}]}

    monkeypatch.setattr(capability, "_post", fake_post)
    capability.run_suite("http://x", "m", "structured_output", limit=1, constrain=True)
    fmt = seen[0]["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["schema"] == capability.SCHEMAS["person"]


def test_json_object_constraint_sends_generic_json_format(monkeypatch):
    seen = []

    def fake_post(base_url, model, payload, timeout):
        seen.append(payload)
        return {"choices": [{"message": {"content": '{"name":"A","age":1,"city":"B"}'}}]}

    monkeypatch.setattr(capability, "_post", fake_post)
    capability.run_suite("http://x", "m", "structured_output", limit=1,
                         constrain=True, constraint_format="json_object")
    assert seen[0]["response_format"] == {"type": "json_object"}


def test_invalid_constraint_format_is_rejected():
    with pytest.raises(ValueError, match="constraint_format"):
        capability.run_suite("http://x", "m", "structured_output", limit=1,
                             constraint_format="freeform")


def test_tool_cases_are_deterministic_and_well_formed():
    cases = capability.CASES["tool_call"]
    assert len(cases) == 18
    assert len({c["prompt"] for c in cases}) == 18
    tools = {t["function"]["name"]: t["function"]["parameters"] for t in capability.TOOLS}
    assert set(tools) == {"get_weather", "convert_currency", "search_notes"}
    for c in cases:
        assert c["tool"] in tools
        assert set(c["expect"]) == set(tools[c["tool"]].get("required", []))


def test_tool_scoring_separates_selection_schema_and_semantics():
    case = capability.CASES["tool_call"][0]  # weather Lisbon celsius
    assert capability.score_tool_case(case, "get_weather", {"city": "Lisbon", "unit": "celsius"}, None)["valid"]
    wrong_tool = capability.score_tool_case(case, "search_notes", {"city": "Lisbon", "unit": "celsius"}, None)
    assert wrong_tool["selection"] is False and wrong_tool["valid"] is False
    wrong_unit = capability.score_tool_case(case, "get_weather", {"city": "Lisbon", "unit": "kelvin"}, None)
    assert wrong_unit["schema_ok"] is False and wrong_unit["valid"] is False
    wrong_city = capability.score_tool_case(case, "get_weather", {"city": "Porto", "unit": "celsius"}, None)
    assert wrong_city["schema_ok"] is True and wrong_city["semantic"] is False


def test_json_tool_format_parses_and_scores(monkeypatch):
    def fake_post(base_url, model, payload, timeout):
        assert payload["response_format"]["type"] == "json_schema"
        return {"choices": [{"message": {"content":
            '{"tool": "convert_currency", "arguments": {"amount": 25, "from": "USD", "to": "EUR"}}'}}]}

    monkeypatch.setattr(capability, "_post", fake_post)
    out = capability.run_suite("http://x", "m", "tool_call", limit=1, tool_format="json")
    m = out["results"]["tool_call"]
    assert m["valid_rate,none"] >= 0.0
    assert "tool_selection_rate" in m


def test_tool_context_fill_prefixes_prompts(monkeypatch):
    seen = []

    def fake_post(base_url, model, payload, timeout):
        seen.append(payload["messages"][0]["content"])
        return {"choices": [{"message": {"tool_calls": [{"function": {
            "name": "get_weather", "arguments": '{"city":"Lisbon","unit":"celsius"}'}}]}}]}

    monkeypatch.setattr(capability, "_post", fake_post)
    capability.run_suite("http://x", "m", "tool_call", limit=1, context_fill=400)
    assert len(seen[0]) > 400 * 3


def test_mechanism_uses_schema_and_preserves_full_response(monkeypatch):
    seen = []
    response = {"choices": [{"message": {"content": "x" * 400},
                             "finish_reason": "length"}],
                "usage": {"completion_tokens": 256}}

    def fake_post(base_url, model, payload, timeout):
        seen.append(payload)
        return response

    monkeypatch.setattr(capability, "_post", fake_post)
    out = capability.run_suite("http://x", "m", "mechanism", limit=1, constrain=True,
                               max_gen_toks=17)
    assert seen[0]["response_format"]["json_schema"]["schema"] == capability.SCHEMAS["sentinel"]
    assert seen[0]["messages"][0]["content"] in [c["prompt"] for c in capability.CASES["mechanism"]]
    assert out["cases"][0]["content"] == "x" * 400
    assert out["cases"][0]["response"] == response
    assert out["cases"][0]["request"] == seen[0]
    assert seen[0]["max_tokens"] == 17


def test_needle_retrieval_prompts_are_paired_by_position():
    cases = capability._needle_retrieval_cases()
    assert len(cases) == 30
    assert {c["depth_pct"] for c in cases} == {10, 50, 90}
    for case_id, value in capability.NEEDLE_CASES:
        pair = [c for c in cases if c["case_id"] == case_id]
        assert {c["needle_value"] for c in pair} == {value}
        assert len({c["prompt"] for c in pair}) == 3
        positions = [c["prompt"].index(f"Record {case_id}") for c in pair]
        assert positions == sorted(positions)


def test_needle_retrieval_scores_and_reports_depth(monkeypatch):
    def fake_post(base_url, model, payload, timeout):
        code = next(value for _, value in capability.NEEDLE_CASES if value in payload["messages"][0]["content"])
        return {"choices": [{"message": {"content": code}},], "usage": {"prompt_tokens": 7000}}

    monkeypatch.setattr(capability, "_post", fake_post)
    out = capability.run_suite("http://x", "m", "needle_retrieval", limit=30)
    assert out["results"]["needle_retrieval"]["valid_rate,none"] == 1.0
    assert out["results"]["needle_retrieval"]["retrieval_by_depth"] == {"10": 1.0, "50": 1.0, "90": 1.0}
    assert all(c["response"]["usage"]["prompt_tokens"] == 7000 for c in out["cases"])


def test_needle_retrieval_depth_filter_selects_one_paired_stratum(monkeypatch):
    def fake_post(base_url, model, payload, timeout):
        code = next(value for _, value in capability.NEEDLE_CASES if value in payload["messages"][0]["content"])
        return {"choices": [{"message": {"content": code}}], "usage": {"prompt_tokens": 7000}}

    monkeypatch.setattr(capability, "_post", fake_post)
    out = capability.run_suite(
        "http://x", "m", "needle_retrieval", limit=10, needle_depth=50
    )
    assert len(out["cases"]) == 10
    assert {case["depth_pct"] for case in out["cases"]} == {50}
    assert out["results"]["needle_retrieval"]["retrieval_by_depth"] == {"50": 1.0}


def test_input_token_endpoint_and_padding_find_exact_rendered_count(monkeypatch):
    seen = []

    def fake_endpoint(url, payload, timeout):
        seen.append((url, payload, timeout))
        return {"input_tokens": len(payload["messages"][0]["content"].split()) + 3}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    payload = {"model": "m", "messages": [{"role": "user", "content":
               "context\nWhat is the code in record K01?"}],
               "max_tokens": 512, "temperature": 0}
    count, response = capability._count_input_tokens("http://x/", payload, 5)
    padded, padded_payload = capability._pad_prompt_to_tokens("http://x", payload, count + 7, 5)
    assert seen[0][0] == "http://x/v1/chat/completions/input_tokens"
    assert response["input_tokens"] == count
    assert padded["count"] == count + 7
    assert padded_payload["messages"][0]["content"].endswith("\nWhat is the code in record K01?")
    assert len(padded["padding"].split()) == 7


def test_distractor_batches_are_disjoint_complete_and_token_matched(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert url.endswith("/v1/chat/completions/input_tokens")
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_completion(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        expected = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": expected}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 5}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_completion)
    outputs = [capability.run_suite("http://x", "m", "needle_distractor", limit=5,
                                    needle_batch=batch) for batch in (0, 1)]
    ids = [{case["case_id"] for case in output["cases"]} for output in outputs]
    assert len(ids[0]) == len(ids[1]) == 5
    assert ids[0].isdisjoint(ids[1])
    assert ids[0] | ids[1] == {case_id for case_id, _ in capability.NEEDLE_CASES}
    for output in outputs:
        cases = output["cases"]
        assert len(cases) == 10
        assert {case["condition"] for case in cases} == {"baseline", "distractor"}
        for case in cases:
            assert case["valid"] and case["exact_match"]
            assert case["condition_input_tokens"] == case["matched_input_tokens"]
            assert case["usage_prompt_tokens"] == case["matched_input_tokens"]
            assert case["usage_matches_input_tokens"]
            assert case["request"]["messages"][0]["content"] == case["prompt"]
            assert case["response"]["usage"]["completion_tokens"] == 5
            assert case["count_provenance"]["baseline"]["response"]["input_tokens"] == case["baseline_input_tokens"]
        assert output["results"]["needle_distractor"]["usage_mismatch_count"] == 0
        assert output["results"]["needle_distractor"]["exact_retrieval_by_condition"] == {
            "baseline": 1.0, "distractor": 1.0}


def test_distractor_padding_failure_prevents_all_generation(monkeypatch):
    generations = []

    def fake_count(base_url, payload, timeout):
        count = 90 if "Record D01" in payload["messages"][0]["content"] else 100
        return count, {"input_tokens": count}

    def fail_padding(*args, **kwargs):
        raise ValueError("cannot match prompt lengths")

    monkeypatch.setattr(capability, "_count_input_tokens", fake_count)
    monkeypatch.setattr(capability, "_pad_prompt_to_tokens", fail_padding)
    monkeypatch.setattr(capability, "_post", lambda *a, **k: generations.append(a))
    with pytest.raises(ValueError, match="cannot match"):
        capability.run_suite("http://x", "m", "needle_distractor", limit=5,
                             needle_batch=0)
    assert generations == []


def test_capability_cmd_passes_needle_batch(tmp_path):
    cmd = campaign.build_capability_cmd(
        campaign.TaskGroup("c", "capability", ["needle_distractor"]), "m", 8090,
        {"limit": 5, "needle_batch": 1}, tmp_path / "r.json",
    )
    assert cmd.count("--needle-batch") == 1
    assert cmd[cmd.index("--needle-batch") + 1] == "1"


def test_archived_conflict_pair_keeps_active_fact_and_query_fixed():
    case_id, current = capability.NEEDLE_CASES[0]
    pair = capability._needle_archived_conflict_pair(case_id, current)
    active = f"Record {case_id}: ACTIVE revision 2025; current field code is {current}. "
    query = f"\nWhat is the active field code in record {case_id}?"
    baseline, conflict = pair["baseline_prompt"], pair["distractor_prompt"]

    assert baseline.endswith(query) and conflict.endswith(query)
    assert baseline.count(active) == conflict.count(active) == 1
    assert baseline.index(active) == conflict.index(active)
    assert "ARCHIVED revision" not in baseline
    assert conflict.count("ARCHIVED revision") == 8
    for _, old_code in capability.NEEDLE_DECOYS:
        assert f"superseded field code was {old_code}" in conflict
        assert old_code != current


def test_archived_conflict_batches_preserve_token_and_response_provenance(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert url.endswith("/v1/chat/completions/input_tokens")
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_completion(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        current = dict(capability.NEEDLE_CASES)[case_id]
        assert payload["max_tokens"] == 512 and payload["temperature"] == 0
        return {"choices": [{"message": {"content": current}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 7}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_completion)
    outputs = [capability.run_suite(
        "http://x", "m", "needle_archived_conflict", limit=5, seed=42,
        max_gen_toks=512, needle_batch=batch,
    ) for batch in (0, 1)]
    ids = [{row["case_id"] for row in output["cases"]} for output in outputs]
    assert ids[0].isdisjoint(ids[1])
    assert ids[0] | ids[1] == {case_id for case_id, _ in capability.NEEDLE_CASES}

    for output in outputs:
        rows = output["cases"]
        assert len(rows) == 10
        assert {row["condition"] for row in rows} == {"baseline", "archived_conflict"}
        assert all(row["exact_match"] and row["valid"] for row in rows)
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["usage_prompt_tokens"] == row["matched_input_tokens"] for row in rows)
        assert all(row["request"]["max_tokens"] == 512 for row in rows)
        assert all("ARCHIVED revision" not in row["prompt"] for row in rows
                   if row["condition"] == "baseline")
        assert all("ARCHIVED revision" in row["prompt"] for row in rows
                   if row["condition"] == "archived_conflict")
        assert all("archived_conflict_after_padding" in row["count_provenance"] for row in rows)
        metrics = output["results"]["needle_archived_conflict"]
        assert metrics["exact_retrieval_by_condition"] == {
            "baseline": 1.0, "archived_conflict": 1.0}
        assert metrics["usage_mismatch_count"] == 0


def test_unlabeled_conflict_pair_differs_only_in_same_id_rows():
    case_id, current = capability.NEEDLE_CASES[0]
    pair = capability._needle_unlabeled_conflict_pair(case_id, current)
    baseline, conflict = pair["baseline_prompt"], pair["distractor_prompt"]

    assert baseline.split("Context:")[0] == conflict.split("Context:")[0]
    assert "ACTIVE" not in conflict and "ARCHIVED" not in conflict
    assert baseline.count(f"Record {case_id}:") == 1
    assert conflict.count(f"Record {case_id}:") == 9
    assert conflict.count(current) == 1
    for _, other in capability.NEEDLE_DECOYS:
        assert f"Record {case_id}: the exact field code is {other}." in conflict
        assert other != current


def test_unlabeled_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert url.endswith("/v1/chat/completions/input_tokens")
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_completion(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        return {"choices": [{"message": {"content": dict(capability.NEEDLE_CASES)[case_id]},
                            "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 5}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_completion)
    outputs = [capability.run_suite(
        "http://x", "m", "needle_unlabeled_conflict", limit=5, seed=42,
        max_gen_toks=512, needle_batch=batch,
    ) for batch in (0, 1)]

    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    assert ids[0] | ids[1] == {case_id for case_id, _ in capability.NEEDLE_CASES}
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "unlabeled_conflict"}
        assert all(row["exact_match"] and row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        metrics = out["results"]["needle_unlabeled_conflict"]
        assert metrics["exact_retrieval_by_condition"] == {
            "baseline": 1.0, "unlabeled_conflict": 1.0}
        assert metrics["usage_mismatch_count"] == 0


def test_no_think_kwargs_reach_both_arms_and_count_requests(monkeypatch):
    payloads = []

    def fake_endpoint(url, payload, timeout):
        payloads.append(payload)
        return {"input_tokens": len(payload["messages"][0]["content"].split()) + 3}

    def fake_post(base_url, model, payload, timeout):
        payloads.append(payload)
        return {"choices": [{"message": {"content": "Q7M4K2"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": len(payload["messages"][0]["content"].split()) + 3}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    out = capability.run_suite("http://x", "m", "needle_unlabeled_conflict", limit=5,
                               needle_batch=0, think=False)
    assert all(p.get("chat_template_kwargs") == {"enable_thinking": False} for p in payloads)
    assert all(p.get("chat_template_kwargs") == {"enable_thinking": False}
               for row in out["cases"] for p in (row["request"],))

    with pytest.raises(ValueError):
        capability.run_suite("http://x", "m", "structured_output", limit=1, think=False)


def test_capability_cmd_forwards_no_think_only_when_disabled(tmp_path):
    group = campaign.TaskGroup("c", "capability", ["needle_unlabeled_conflict"])
    on = campaign.build_capability_cmd(group, "m", 8090, {"limit": 5, "think": True},
                                       tmp_path / "r.json")
    off = campaign.build_capability_cmd(group, "m", 8090, {"limit": 5, "think": False},
                                        tmp_path / "r.json")
    assert "--no-think" not in on
    assert off.count("--no-think") == 1


def test_position_conflict_moves_only_the_designated_code():
    case_id, value = capability.NEEDLE_CASES[0]
    pair = capability._needle_position_conflict_pair(case_id, value)
    baseline, moved = pair["baseline_prompt"], pair["distractor_prompt"]
    marker = f"Record {case_id}: the exact field code is "
    decoy_codes = [code for _, code in capability.NEEDLE_DECOYS]

    for prompt in (baseline, moved):
        assert prompt.count(marker) == 9
        assert prompt.count(value) == 1
        assert prompt.endswith(f"\nWhat is the code in record {case_id}?")
        assert "ACTIVE" not in prompt and "ARCHIVED" not in prompt
        assert sorted(c for c in decoy_codes if c in prompt) == sorted(decoy_codes)

    def ranks(prompt):
        return [prompt.index(marker + code) for code in [value, *decoy_codes]]

    assert sorted(ranks(baseline)) == sorted(ranks(moved))
    assert baseline.index(marker + value) < min(
        baseline.index(marker + code) for code in decoy_codes)
    assert moved.index(marker + value) > max(
        moved.index(marker + code) for code in decoy_codes)


def test_position_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert url.endswith("/v1/chat/completions/input_tokens")
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_position_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    assert ids[0] | ids[1] == {case_id for case_id, _ in capability.NEEDLE_CASES}
    for out in outputs:
        rows = out["cases"]
        assert len(rows) == 10
        assert {row["condition"] for row in rows} == {"baseline", "position_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("position_conflict_after_padding" in row["count_provenance"] for row in rows)
        metrics = out["results"]["needle_position_conflict"]
        assert set(metrics["exact_retrieval_by_condition"]) == {"baseline", "position_conflict"}
        assert metrics["usage_mismatch_count"] == 0


def test_recency_conflict_moves_only_the_newest_code():
    case_id, value = capability.NEEDLE_CASES[0]
    pair = capability._needle_recency_conflict_pair(case_id, value)
    baseline, moved = pair["baseline_prompt"], pair["distractor_prompt"]
    marker = f"Record {case_id}: updated "
    decoy_codes = [code for _, code in capability.NEEDLE_DECOYS]
    dates = (capability.NEEDLE_CURRENT_DATE, *capability.NEEDLE_DECOY_DATES)

    def entries(prompt):
        return [(d, c) for d, c in
                __import__("re").findall(r"updated (\S+); field code is (\S+)\.", prompt)]

    assert len(baseline) == len(moved)
    assert entries(baseline) and sorted(entries(baseline)) == sorted(entries(moved))
    for prompt in (baseline, moved):
        assert prompt.count(marker) == 9
        assert prompt.endswith(f"\nWhat is the code in record {case_id}?")
        assert "ACTIVE" not in prompt and "ARCHIVED" not in prompt
        assert sorted(d for d, _ in entries(prompt)) == sorted(dates)
        assert sorted(c for _, c in entries(prompt)) == sorted([value, *decoy_codes])

    assert entries(baseline)[0] == (capability.NEEDLE_CURRENT_DATE, value)
    assert entries(moved)[-1] == (capability.NEEDLE_CURRENT_DATE, value)
    assert entries(moved)[0][1] != value


def test_recency_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert url.endswith("/v1/chat/completions/input_tokens")
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_recency_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    assert ids[0] | ids[1] == {case_id for case_id, _ in capability.NEEDLE_CASES}
    for out in outputs:
        rows = out["cases"]
        assert len(rows) == 10
        assert {row["condition"] for row in rows} == {"baseline", "recency_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("recency_conflict_after_padding" in row["count_provenance"] for row in rows)
        metrics = out["results"]["needle_recency_conflict"]
        assert set(metrics["exact_retrieval_by_condition"]) == {"baseline", "recency_conflict"}
        assert metrics["usage_mismatch_count"] == 0


def test_rank_conflict_keeps_designated_index_and_moves_only_rank():
    import re

    case_id, value = capability.NEEDLE_CASES[0]
    pair = capability._needle_rank_conflict_pair(case_id, value)
    baseline, early = pair["baseline_prompt"], pair["distractor_prompt"]
    decoy_codes = [code for _, code in capability.NEEDLE_DECOYS]
    pattern = rf"Record {case_id}: the exact field code is ([A-Z0-9]+)\."

    def codes(prompt):
        return re.findall(pattern, prompt)

    assert len(baseline) == len(early)
    assert sorted(codes(baseline)) == sorted(codes(early)) == sorted([value, *decoy_codes])
    assert codes(baseline)[0] == value
    assert codes(early)[0] == decoy_codes[-1]
    assert codes(early)[1] == value
    for prompt in (baseline, early):
        assert prompt.endswith(f"\nWhat is the code in record {case_id}?")
        assert "ACTIVE" not in prompt and "ARCHIVED" not in prompt


def test_rank_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert url.endswith("/v1/chat/completions/input_tokens")
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_rank_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    assert ids[0] | ids[1] == {case_id for case_id, _ in capability.NEEDLE_CASES}
    for out in outputs:
        rows = out["cases"]
        assert len(rows) == 10
        assert {row["condition"] for row in rows} == {"baseline", "rank_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("rank_conflict_after_padding" in row["count_provenance"] for row in rows)
        metrics = out["results"]["needle_rank_conflict"]
        assert set(metrics["exact_retrieval_by_condition"]) == {"baseline", "rank_conflict"}
        assert metrics["usage_mismatch_count"] == 0


def test_precedence_conflict_adds_rule_without_moving_records():
    case_id, value = capability.NEEDLE_CASES[0]
    recency = capability._needle_recency_conflict_pair(case_id, value)
    pair = capability._needle_precedence_conflict_pair(case_id, value)

    for key in ("baseline_prompt", "distractor_prompt"):
        assert "If several records share the requested ID, use the one with the most recent date." in pair[key]
        # Only the instruction changed; the body is byte-identical.
        assert pair[key].split("Context:\n")[1] == recency[key].split("Context:\n")[1]
    assert len(pair["baseline_prompt"]) == len(pair["distractor_prompt"])
    assert pair["baseline_prompt"].index(value) < pair["distractor_prompt"].index(value)


def test_precedence_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_precedence_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "precedence_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("precedence_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_precedence_conflict"]["usage_mismatch_count"] == 0


def test_precedence_tail_conflict_moves_only_the_rule():
    case_id, value = capability.NEEDLE_CASES[0]
    recency = capability._needle_recency_conflict_pair(case_id, value)
    pair = capability._needle_precedence_tail_conflict_pair(case_id, value)
    rule = "If several records share the requested ID, use the one with the most recent date."

    for key in ("baseline_prompt", "distractor_prompt"):
        prompt = pair[key]
        # The body is byte-identical to the rule-free recency suite.
        query = f"\nWhat is the code in record {case_id}?"
        body = prompt.split("Context:\n")[1].split("\nIf several records")[0]
        assert body == recency[key].split("Context:\n")[1].split(query)[0]
        # The rule sits after the context, immediately before the query.
        assert prompt.count(rule) == 1
        assert prompt.index(rule) > prompt.index("Context:\n")
        assert prompt.rstrip().endswith(f"What is the code in record {case_id}?")
        assert prompt.index(rule) < prompt.rindex(f"What is the code in record {case_id}?")
    assert len(pair["baseline_prompt"]) == len(pair["distractor_prompt"])
    assert pair["baseline_prompt"].index(value) < pair["distractor_prompt"].index(value)


def test_precedence_tail_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_precedence_tail_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    assert ids[0] | ids[1] == {case_id for case_id, _ in capability.NEEDLE_CASES}
    for out in outputs:
        rows = out["cases"]
        assert len(rows) == 10
        assert {row["condition"] for row in rows} == {"baseline", "precedence_tail_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("precedence_tail_conflict_after_padding" in row["count_provenance"] for row in rows)
        metrics = out["results"]["needle_precedence_tail_conflict"]
        assert set(metrics["exact_retrieval_by_condition"]) == {"baseline", "precedence_tail_conflict"}
        assert metrics["usage_mismatch_count"] == 0


def test_archived_rank_conflict_moves_only_the_order():
    case_id, value = capability.NEEDLE_CASES[0]
    pair = capability._needle_archived_rank_conflict_pair(case_id, value)
    baseline, early = pair["baseline_prompt"], pair["distractor_prompt"]

    assert len(baseline) == len(early)
    for prompt in (baseline, early):
        assert prompt.count("ACTIVE") == 1 and prompt.count("ARCHIVED") == 8
        assert prompt.count(value) == 1
        assert prompt.endswith(f"\nWhat is the active field code in record {case_id}?")
    # Same nine rows, only reordered.
    import re
    row = re.compile(rf"Record {case_id}: (?:ACTIVE|ARCHIVED)[^.]*\.")
    assert sorted(row.findall(baseline)) == sorted(row.findall(early))
    assert baseline.index("ACTIVE") < baseline.index("ARCHIVED")
    assert early.index("ARCHIVED") < early.index("ACTIVE")


def test_archived_rank_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_archived_rank_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "archived_rank_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("archived_rank_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_archived_rank_conflict"]["usage_mismatch_count"] == 0


def test_status_label_conflict_keeps_question_free_of_the_label():
    import re

    case_id, value = capability.NEEDLE_CASES[0]
    pair = capability._needle_status_label_conflict_pair(case_id, value)
    baseline, early = pair["baseline_prompt"], pair["distractor_prompt"]

    assert len(baseline) == len(early)
    row = re.compile(rf"Record {case_id}: status (ACTIVE|ARCHIVED); value is ([A-Z0-9]+)\.")
    for prompt in (baseline, early):
        assert prompt.count("status ACTIVE") == 1 and prompt.count("status ARCHIVED") == 8
        assert prompt.count(value) == 1
        question = prompt[prompt.rindex("\nWhat is"):].lower()
        assert "active" not in question and "archived" not in question
        assert prompt.endswith(f"\nWhat is the value in record {case_id}?")
    assert sorted(row.findall(baseline)) == sorted(row.findall(early))
    assert baseline.index("status ACTIVE") < baseline.index("status ARCHIVED")
    assert early.index("status ARCHIVED") < early.index("status ACTIVE")


def test_status_label_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_status_label_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "status_label_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("status_label_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_status_label_conflict"]["usage_mismatch_count"] == 0


def test_authoritative_flag_conflict_marks_one_candidate_true():
    import json
    import re

    case_id, value = capability.NEEDLE_CASES[0]
    pair = capability._needle_authoritative_flag_conflict_pair(case_id, value)
    baseline, early = pair["baseline_prompt"], pair["distractor_prompt"]
    candidate = re.compile(r'\{"record": "[A-Z0-9]+", "code": "[A-Z0-9]+", "authoritative": (?:true|false)\}')

    assert len(baseline) == len(early)
    for prompt in (baseline, early):
        found = [json.loads(text) for text in candidate.findall(prompt)]
        assert len(found) == 9
        assert [row["authoritative"] for row in found].count(True) == 1
        assert {row["record"] for row in found} == {case_id}
        assert sorted(row["code"] for row in found) == sorted([value, *[c for _, c in capability.NEEDLE_DECOYS]])
        assert prompt.endswith(f"\nWhat is the code in record {case_id}?")
        assert "authoritative" not in prompt.split("Context:\n")[0]
    assert json.loads(candidate.findall(baseline)[0]) == {"record": case_id, "code": value, "authoritative": True}
    assert json.loads(candidate.findall(early)[0])["authoritative"] is False
    assert json.loads(candidate.findall(early)[-1]) == {"record": case_id, "code": value, "authoritative": True}


def test_authoritative_flag_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_authoritative_flag_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "authoritative_flag_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("authoritative_flag_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_authoritative_flag_conflict"]["usage_mismatch_count"] == 0


def test_authoritative_query_conflict_changes_only_the_question():
    import re

    case_id, value = capability.NEEDLE_CASES[0]
    plain = capability._needle_authoritative_flag_conflict_pair(case_id, value)
    cued = capability._needle_authoritative_query_conflict_pair(case_id, value)

    for key in ("baseline_prompt", "distractor_prompt"):
        assert cued[key].split("\nWhat is the code")[0] == plain[key].split("\nWhat is the code")[0]
        assert cued[key].endswith(
            f"\nWhat is the code in record {case_id} whose authoritative flag is true?")
    assert len(cued["baseline_prompt"]) == len(cued["distractor_prompt"])
    candidate = re.compile(r'\{"record": "[A-Z0-9]+", "code": "[A-Z0-9]+", "authoritative": (?:true|false)\}')
    baseline_candidates = candidate.findall(cued["baseline_prompt"])
    challenge_candidates = candidate.findall(cued["distractor_prompt"])
    assert baseline_candidates[0] == challenge_candidates[-1] and '"authoritative": true' in baseline_candidates[0]


def test_authoritative_query_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split(" ", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_authoritative_query_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "authoritative_query_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("authoritative_query_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_authoritative_query_conflict"]["usage_mismatch_count"] == 0


def test_authoritative_literal_conflict_quotes_the_context_fragment():
    import re

    case_id, value = capability.NEEDLE_CASES[0]
    plain = capability._needle_authoritative_flag_conflict_pair(case_id, value)
    quoted = capability._needle_authoritative_literal_conflict_pair(case_id, value)
    fragment = '"authoritative": true'

    for key in ("baseline_prompt", "distractor_prompt"):
        assert quoted[key].split("\nWhat is the code")[0] == plain[key].split("\nWhat is the code")[0]
        assert quoted[key].count(fragment) == 2
        assert quoted[key].endswith(
            f'\nWhat is the code in record {case_id} in the line containing {fragment}?')
    assert len(quoted["baseline_prompt"]) == len(quoted["distractor_prompt"])
    candidate = re.compile(r'\{"record": "[A-Z0-9]+", "code": "[A-Z0-9]+", "authoritative": (?:true|false)\}')
    baseline_candidates = candidate.findall(quoted["baseline_prompt"])
    challenge_candidates = candidate.findall(quoted["distractor_prompt"])
    assert baseline_candidates[0] == challenge_candidates[-1] and fragment in baseline_candidates[0]


def test_authoritative_literal_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split(" ", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_authoritative_literal_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "authoritative_literal_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("authoritative_literal_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_authoritative_literal_conflict"]["usage_mismatch_count"] == 0


def test_prose_conflict_renders_the_recency_panel_as_chunks():
    import re

    case_id, value = capability.NEEDLE_CASES[0]
    pair = capability._needle_prose_conflict_pair(case_id, value)
    baseline, moved = pair["baseline_prompt"], pair["distractor_prompt"]
    pattern = re.compile(
        rf"## Record {case_id} — audit note \((\S+)\)\n\n"
        rf"The records team last updated this note on \S+\. "
        rf"The field code for record {case_id} is ([A-Z0-9]+)\."
    )
    expected = sorted(zip(
        (capability.NEEDLE_CURRENT_DATE, *capability.NEEDLE_DECOY_DATES),
        (value, *[code for _, code in capability.NEEDLE_DECOYS]),
    ))
    for prompt in (baseline, moved):
        assert sorted(pattern.findall(prompt)) == expected
        assert prompt.endswith(f"\nWhat is the code in record {case_id}?")
        assert "ACTIVE" not in prompt and "ARCHIVED" not in prompt
        assert "most recent" not in prompt
    assert len(baseline) == len(moved)
    assert pattern.findall(baseline)[0] == (capability.NEEDLE_CURRENT_DATE, value)
    assert pattern.findall(moved)[-1] == (capability.NEEDLE_CURRENT_DATE, value)
    assert pattern.findall(moved)[0][1] != value


def test_prose_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert url.endswith("/v1/chat/completions/input_tokens")
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_prose_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "prose_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("prose_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_prose_conflict"]["usage_mismatch_count"] == 0


def test_adjacent_pair_conflict_swaps_two_neighbouring_chunks():
    import re

    case_id, value = capability.NEEDLE_CASES[0]
    pair = capability._needle_adjacent_pair_conflict_pair(case_id, value)
    baseline, swapped = pair["baseline_prompt"], pair["distractor_prompt"]
    pattern = re.compile(
        rf"## Record {case_id} — audit note \((\S+)\)\n\n"
        rf"The records team last updated this note on \S+\. "
        rf"The field code for record {case_id} is ([A-Z0-9]+)\."
    )
    older = (capability.NEEDLE_DECOY_DATES[-1], capability.NEEDLE_DECOYS[-1][1])
    newest = (capability.NEEDLE_CURRENT_DATE, value)

    assert len(baseline) == len(swapped)
    assert pattern.findall(baseline) == [newest, older]
    assert pattern.findall(swapped) == [older, newest]
    for prompt in (baseline, swapped):
        assert prompt.count(f"## Record {case_id} —") == 2
        assert prompt.endswith(f"\nWhat is the code in record {case_id}?")
        assert prompt.count(value) == 1
        assert "most recent" not in prompt and "ACTIVE" not in prompt


def test_adjacent_pair_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert url.endswith("/v1/chat/completions/input_tokens")
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_adjacent_pair_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "adjacent_pair_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("adjacent_pair_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_adjacent_pair_conflict"]["usage_mismatch_count"] == 0


def test_distant_pair_conflict_swaps_two_separated_chunks():
    import re

    case_id, value = capability.NEEDLE_CASES[0]
    pair = capability._needle_distant_pair_conflict_pair(case_id, value)
    baseline, swapped = pair["baseline_prompt"], pair["distractor_prompt"]
    pattern = re.compile(
        rf"## Record {case_id} — audit note \((\S+)\)\n\n"
        rf"The records team last updated this note on \S+\. "
        rf"The field code for record {case_id} is ([A-Z0-9]+)\."
    )
    older = (capability.NEEDLE_DECOY_DATES[-1], capability.NEEDLE_DECOYS[-1][1])
    newest = (capability.NEEDLE_CURRENT_DATE, value)

    assert len(baseline) == len(swapped)
    assert pattern.findall(baseline) == [newest, older]
    assert pattern.findall(swapped) == [older, newest]
    # The two chunks stay far apart; only their order changes.
    starts = [match.start() for match in pattern.finditer(baseline)]
    assert starts[1] - starts[0] > len(baseline) // 4
    assert [match.start() for match in pattern.finditer(swapped)][1] - starts[0] > len(swapped) // 4
    for prompt in (baseline, swapped):
        assert prompt.endswith(f"\nWhat is the code in record {case_id}?")
        assert prompt.count(value) == 1


def test_distant_pair_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert url.endswith("/v1/chat/completions/input_tokens")
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_distant_pair_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "distant_pair_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("distant_pair_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_distant_pair_conflict"]["usage_mismatch_count"] == 0


def test_short_context_conflict_uses_the_same_chunks_in_a_short_prompt():
    import re

    case_id, value = capability.NEEDLE_CASES[0]
    short = capability._needle_short_context_conflict_pair(case_id, value)
    long = capability._needle_adjacent_pair_conflict_pair(case_id, value)
    baseline, swapped = short["baseline_prompt"], short["distractor_prompt"]
    pattern = re.compile(
        rf"## Record {case_id} — audit note \((\S+)\)\n\n"
        rf"The records team last updated this note on \S+\. "
        rf"The field code for record {case_id} is ([A-Z0-9]+)\."
    )
    older = (capability.NEEDLE_DECOY_DATES[-1], capability.NEEDLE_DECOYS[-1][1])
    newest = (capability.NEEDLE_CURRENT_DATE, value)

    assert len(baseline) == len(swapped)
    assert len(baseline) < len(long["baseline_prompt"]) / 2
    assert pattern.findall(baseline) == [newest, older]
    assert pattern.findall(swapped) == [older, newest]
    for prompt in (baseline, swapped):
        assert prompt.count(capability.FILLER) == capability.NEEDLE_SHORT_FILLERS - 2
        assert prompt.endswith(f"\nWhat is the code in record {case_id}?")
        assert prompt.count(value) == 1


def test_short_context_conflict_batches_match_tokens_and_track_condition(monkeypatch):
    def token_count(prompt):
        return len(prompt.split()) + 3

    def fake_endpoint(url, payload, timeout):
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        return {"input_tokens": token_count(payload["messages"][0]["content"])}

    def fake_post(base_url, model, payload, timeout):
        prompt = payload["messages"][0]["content"]
        case_id = prompt.rsplit("record ", 1)[1].split("?", 1)[0]
        code = dict(capability.NEEDLE_CASES)[case_id]
        return {"choices": [{"message": {"content": code}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": token_count(prompt), "completion_tokens": 6}}

    monkeypatch.setattr(capability, "_post_endpoint", fake_endpoint)
    monkeypatch.setattr(capability, "_post", fake_post)
    outputs = [capability.run_suite("http://x", "m", "needle_short_context_conflict", limit=5,
                                    needle_batch=batch, think=False, max_gen_toks=512)
               for batch in (0, 1)]
    ids = [{row["case_id"] for row in out["cases"]} for out in outputs]
    assert len(ids[0]) == len(ids[1]) == 5 and ids[0].isdisjoint(ids[1])
    for out in outputs:
        rows = out["cases"]
        assert {row["condition"] for row in rows} == {"baseline", "short_context_conflict"}
        assert all(row["usage_matches_input_tokens"] for row in rows)
        assert all(row["matched_input_tokens"] == row["usage_prompt_tokens"] for row in rows)
        assert all("short_context_conflict_after_padding" in row["count_provenance"] for row in rows)
        assert out["results"]["needle_short_context_conflict"]["usage_mismatch_count"] == 0

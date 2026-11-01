"""Unit tests for the campaign orchestration layer.

These never touch a GPU, llama.cpp or the harness: they pin the spec contract,
the resume key, the official-CLI command shapes and the aggregation of already
produced JSON.
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

from llm_research_bench import campaign


VALID_SPEC = {
    "campaign": "unit-test",
    "hardware_profile": "cpu-ci",
    "status": "measured",
    "server": {"port": 8090, "ctx_size": 4096},
    "bench": {"prompt_tokens": 512, "gen_tokens": 128, "repetitions": 3},
    "evaluation": {"limit": 20, "seed": 42, "num_fewshot": 0, "batch_size": 1},
    "models": [
        {
            "name": "qwen3-1.7b-q4km",
            "alias": "qwen3-1.7b",
            "file": "Qwen3-1.7B-Q4_K_M.gguf",
            "quantization": "Q4_K_M",
            "hf_repo": "ggml-org/Qwen3-1.7B-GGUF",
            "hf_revision": "daeb8e2",
        }
    ],
    "task_groups": [
        {"name": "knowledge-mcq", "backend": "gguf", "tasks": ["arc_challenge", "hellaswag"]},
        {
            "name": "generative-chat",
            "backend": "local-chat-completions",
            "tasks": ["gsm8k", "ifeval"],
        },
    ],
}


def write_spec(tmp_path: Path, mutate=None) -> Path:
    payload = json.loads(json.dumps(VALID_SPEC))
    if mutate:
        mutate(payload)
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def test_load_spec_parses_models_and_groups(tmp_path):
    spec = campaign.load_spec(write_spec(tmp_path))
    assert spec.campaign == "unit-test"
    assert [m.name for m in spec.models] == ["qwen3-1.7b-q4km"]
    assert spec.task_groups[1].backend == "local-chat-completions"


@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda p: p.pop("hardware_profile"), "hardware_profile"),
        (lambda p: p["models"].append(dict(p["models"][0])), "duplicate model name"),
        (lambda p: p["task_groups"][0].update(backend="vllm"), "backend must be"),
        (lambda p: p["evaluation"].update(limit=0), "evaluation.limit"),
        (lambda p: p["models"][0].pop("quantization"), "quantization"),
        (lambda p: p["task_groups"][0].update(tasks=[]), "no tasks"),
    ],
)
def test_invalid_specs_are_rejected(tmp_path, mutate, needle):
    with pytest.raises(campaign.SpecError) as excinfo:
        campaign.load_spec(write_spec(tmp_path, mutate))
    assert needle in str(excinfo.value)


def test_status_must_separate_measured_from_hypothesis(tmp_path):
    with pytest.raises(campaign.SpecError):
        campaign.load_spec(write_spec(tmp_path, lambda p: p.update(status="guess")))


def test_config_hash_is_stable_and_sensitive():
    spec = campaign.CampaignSpec(
        campaign="c",
        hardware_profile="h",
        models=[campaign.ModelSpec("m", "f.gguf", "Q4_K_M", alias="m")],
        task_groups=[campaign.TaskGroup("g", "gguf", ["arc_challenge"])],
        evaluation={"limit": 20, "seed": 42},
    )
    runtime = {"lm_eval": "0.4.x"}
    first = campaign.run_key(spec.models[0], spec.task_groups[0], spec, runtime)
    assert first == campaign.run_key(spec.models[0], spec.task_groups[0], spec, runtime)

    spec.evaluation["limit"] = 40
    assert first != campaign.run_key(spec.models[0], spec.task_groups[0], spec, runtime)


def test_existing_result_requires_matching_key_and_measured_status(tmp_path):
    group_dir = tmp_path / "group"
    group_dir.mkdir()
    (group_dir / "results.json").write_text("{}", encoding="utf-8")
    (group_dir / "meta.json").write_text(
        json.dumps({"run_key": "abc", "status": "measured"}), encoding="utf-8"
    )
    assert campaign.existing_result(group_dir, "abc")
    assert not campaign.existing_result(group_dir, "def")

    (group_dir / "meta.json").write_text(
        json.dumps({"run_key": "abc", "status": "failed"}), encoding="utf-8"
    )
    assert not campaign.existing_result(group_dir, "abc")


def test_server_and_bench_commands_use_official_flags(tmp_path):
    server = campaign.build_server_cmd(
        "llama-server", tmp_path / "m.gguf", "alias", {"port": 8091, "ctx_size": 8192}
    )
    assert server[:2] == ["llama-server", "-m"]
    assert "--jinja" in server and "--alias" in server
    assert server[server.index("--ctx-size") + 1] == "8192"

    bench = campaign.build_bench_cmd(
        "llama-bench", tmp_path / "m.gguf", {"prompt_tokens": 512, "gen_tokens": 128}
    )
    assert bench[-2:] == ["-o", "json"]
    assert bench[bench.index("-p") + 1] == "512"


def test_lm_eval_command_matrix():
    evaluation = {"limit": 20, "seed": 42, "num_fewshot": 0, "batch_size": 1}
    mcq = campaign.build_lm_eval_cmd(
        campaign.TaskGroup("k", "gguf", ["arc_challenge"]), "alias", 8090, evaluation, Path("raw")
    )
    assert mcq[mcq.index("--model") + 1] == "gguf"
    args = mcq[mcq.index("--model_args") + 1]
    assert "base_url=http://127.0.0.1:8090" in args
    assert "/v1/chat/completions" not in args

    chat = campaign.build_lm_eval_cmd(
        campaign.TaskGroup("g", "local-chat-completions", ["gsm8k"]),
        "alias",
        8090,
        evaluation,
        Path("raw"),
    )
    args = chat[chat.index("--model_args") + 1]
    assert args.endswith("base_url=http://127.0.0.1:8090/v1/chat/completions")
    assert "model=alias" in args
    assert chat[chat.index("--limit") + 1] == "20"


def test_wilson_interval_brackets_estimate():
    interval = campaign.wilson_interval(0.5, 20)
    assert interval == pytest.approx([0.2993, 0.7007], abs=1e-4)
    assert campaign.wilson_interval(1.0, 20)[1] == 1.0
    assert campaign.wilson_interval(0.5, 0) is None


def _write_group(root: Path, model: str, group: str, task: str, value: float, **meta):
    group_dir = root / "campaign-a" / "hw-a" / model / group
    group_dir.mkdir(parents=True)
    (group_dir / "results.json").write_text(
        json.dumps(
            {
                "results": {
                    task: {
                        "alias": "arc_challenge",
                        "acc,none": value,
                        "acc_stderr,none": 0.1,
                        "n-samples": {"effective": 20},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    manifest = {
        "campaign": "campaign-a",
        "hardware_profile": "hw-a",
        "status": "measured",
        "model": {"name": model},
        "evaluation": {"limit": 20},
    }
    manifest.update(meta)
    (group_dir / "meta.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_summarize_uses_harness_metrics_and_skips_failures(tmp_path):
    _write_group(tmp_path, "model-a", "knowledge-mcq", "arc_challenge", 0.5)
    _write_group(tmp_path, "model-b", "knowledge-mcq", "arc_challenge", 0.9, status="failed")

    summary = campaign.summarize(tmp_path)
    assert summary["campaigns"] == ["campaign-a"]
    assert len(summary["quality"]) == 1
    row = summary["quality"][0]
    assert row["model"] == "model-a"
    assert row["n"] == 20
    assert row["ci95"][0] < row["value"] < row["ci95"][1]

    markdown = campaign.render_markdown(summary)
    assert "| campanha | hardware | modelo" in markdown
    assert "não autorizam ranking" in markdown


def test_find_results_json_picks_harness_file(tmp_path):
    raw = tmp_path / "raw"
    nested = raw / "model" / "samples"
    nested.mkdir(parents=True)
    (nested / "results_2026.json").write_text(json.dumps({"results": {"arc": {}}}), encoding="utf-8")
    assert campaign.find_results_json(raw) == nested / "results_2026.json"


def test_audit_reports_missing_legacy_provenance(tmp_path):
    (tmp_path / "legacy.json").write_text(
        json.dumps({"suite_version": "v1.0", "results": {"arc": 0.4}}), encoding="utf-8"
    )
    findings = [f for f in campaign.audit_results(tmp_path) if f["format"] == "legacy"]
    assert findings and "seed" in findings[0]["missing"]
    assert "timestamp" in findings[0]["missing"]


def test_llama_device_listing_is_parsed_when_nvidia_smi_is_absent(monkeypatch):
    listing = "Available devices:\n  CUDA0: NVIDIA GeForce GTX 1050 Ti (4023 MiB, 3975 MiB free)\n"

    class FakeProc:
        stdout = listing
        stderr = ""
        returncode = 0

    monkeypatch.setattr(
        campaign.shutil, "which", lambda name: None if name == "nvidia-smi" else "/usr/bin/" + name
    )
    monkeypatch.setattr(campaign.subprocess, "run", lambda *a, **k: FakeProc())
    gpu = campaign.query_gpu()
    assert gpu["source"] == "llama-server --list-devices"
    assert gpu["devices"] == [
        {
            "id": "CUDA0",
            "name": "NVIDIA GeForce GTX 1050 Ti",
            "memory_total": "4023 MiB",
            "memory_free": "3975 MiB",
        }
    ]

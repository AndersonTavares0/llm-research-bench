import json
import hashlib
from pathlib import Path

from llm_research_bench import rag_evaluator


def _row(case_id="hp1"):
    return {
        "id": case_id,
        "type": "bridge",
        "level": "hard",
        "question": "Which city is associated with the author?",
        "answer": "Paris",
        "supporting_facts": {"title": ["Author", "Book"], "sent_id": [0, 0]},
        "context": {
            "title": ["Author", "Noise", "Book"],
            "sentences": [
                ["The author was born in Paris."],
                ["This unrelated page describes a mountain."],
                ["The book was written by the author."],
            ],
        },
    }


def test_prompt_reorders_document_groups_without_reordering_within_groups():
    row = _row()
    first = rag_evaluator.render_prompt(row, True)
    last = rag_evaluator.render_prompt(row, False)
    assert first.index("## Author") < first.index("## Book") < first.index("## Noise")
    assert last.index("## Noise") < last.index("## Author") < last.index("## Book")


def test_hotpotqa_answer_normalization_and_evidence_scoring():
    scored = rag_evaluator.score_response(
        '{"answer":"The Paris!","supporting_titles":["Author","Book"]}',
        "Paris", ["Author", "Book"],
    )
    assert scored["answer_exact_match"]
    assert scored["support_titles_f1"] == 1
    assert scored["joint_exact"]

    invalid = rag_evaluator.score_response("not json", "Paris", ["Author"])
    assert invalid["parse_error"]
    assert invalid["parse_status"] == "malformed_json"
    assert not invalid["answer_exact_match"]
    assert not invalid["joint_exact"]

    invalid_shape = rag_evaluator.score_response('{"answer": 1}', "Paris", ["Author"])
    assert invalid_shape["parse_status"] == "invalid_response_shape"


def test_run_batch_preserves_paired_raw_evidence_and_scores(monkeypatch, tmp_path):
    dataset = tmp_path / "rows.jsonl"
    dataset.write_text(json.dumps(_row()) + "\n", encoding="utf-8")

    def count_tokens(base_url, payload, timeout):
        return 42, {"request_payload": payload, "input_tokens": 42}

    def post(base_url, model, payload, timeout):
        return {
            "choices": [{"message": {"content": json.dumps(
                {"answer": "Paris", "supporting_titles": ["Author", "Book"]})},
                "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 42, "completion_tokens": 12},
        }

    monkeypatch.setattr(rag_evaluator.capability, "_count_input_tokens", count_tokens)
    monkeypatch.setattr(rag_evaluator.capability, "_post", post)
    result = rag_evaluator.run_batch("http://local", "model", dataset, 0, batch_size=1)

    assert len(result["cases"]) == 2
    assert {case["condition"] for case in result["cases"]} == {"support_first", "support_last"}
    assert all(case["answer_exact_match"] and case["joint_exact"] for case in result["cases"])
    assert all(case["response_status"] == "ok" for case in result["cases"])
    assert all(case["usage_matches_input_tokens"] for case in result["cases"])
    assert all("request" in case["token_count_provenance"]["after"] for case in result["cases"])
    assert all(case["request"] and case["response"] and case["gold_support_facts"]
               for case in result["cases"])
    assert result["dataset"]["sha256"] == hashlib.sha256(dataset.read_bytes()).hexdigest()


def test_run_batch_classifies_length_finish_as_truncation(monkeypatch, tmp_path):
    dataset = tmp_path / "rows.jsonl"
    dataset.write_text(json.dumps(_row()) + "\n", encoding="utf-8")

    monkeypatch.setattr(rag_evaluator.capability, "_count_input_tokens",
                        lambda *args: (42, {"input_tokens": 42}))
    monkeypatch.setattr(rag_evaluator.capability, "_post", lambda *args: {
        "choices": [{"message": {"content": '{"answer":'}, "finish_reason": "length"}]
    })

    result = rag_evaluator.run_batch("http://local", "model", dataset, 0, batch_size=1)
    assert all(case["parse_status"] == "malformed_json" for case in result["cases"])
    assert all(case["response_status"] == "truncated" for case in result["cases"])


def test_run_batch_fails_closed_on_manifest_hash_mismatch(tmp_path):
    dataset = tmp_path / "rows.jsonl"
    dataset.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
    dataset.with_suffix(".manifest.json").write_text('{"sha256":"wrong"}', encoding="utf-8")
    try:
        rag_evaluator.run_batch("http://local", "model", dataset, 0, batch_size=1)
    except ValueError as exc:
        assert "manifest SHA-256" in str(exc)
    else:
        raise AssertionError("dataset/manifest mismatch was accepted")


def test_run_batch_pads_shorter_arm_and_records_verified_count(monkeypatch, tmp_path):
    dataset = tmp_path / "rows.jsonl"
    dataset.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
    counts_seen = []

    def count_tokens(base_url, payload, timeout):
        prompt = payload["messages"][0]["content"]
        count = 42 if prompt.index("## Author") < prompt.index("## Noise") else 41
        counts_seen.append(count)
        return count, {"input_tokens": count}

    def pad_tokens(base_url, payload, target, timeout):
        prompt = payload["messages"][0]["content"]
        padded = {**payload, "messages": [{"role": "user", "content": prompt + "\n"}]}
        return {"prompt": padded["messages"][0]["content"], "count": target,
                "padding": "\n", "response": {"input_tokens": target}}, padded

    def post(base_url, model, payload, timeout):
        return {"choices": [{"message": {"content": '{"answer":"Paris","supporting_titles":["Author","Book"]}'}}],
                "usage": {"prompt_tokens": 42}}

    monkeypatch.setattr(rag_evaluator.capability, "_count_input_tokens", count_tokens)
    monkeypatch.setattr(rag_evaluator.capability, "_pad_prompt_to_tokens", pad_tokens)
    monkeypatch.setattr(rag_evaluator.capability, "_post", post)
    result = rag_evaluator.run_batch("http://local", "model", dataset, 0, batch_size=1)

    assert 41 in counts_seen and 42 in counts_seen
    assert all(case["matched_input_tokens"] == 42 for case in result["cases"])
    padded_case = next(case for case in result["cases"] if case["padding"])
    assert padded_case["token_count_provenance"]["after"]["count"] == 42
    assert padded_case["token_count_provenance"]["after"]["response"]["input_tokens"] == 42

# Official benchmark campaigns

This page documents the lightweight orchestration layer over community-maintained tools. It **does not replace or relabel** the repository's historical results, which were produced by the project's own evaluators and protocols described in the existing reports.

## Smoke campaign: Qwen3-1.7B

Complete artifacts, including raw outputs, samples, and manifests:
[`results/campaigns/smoke-qwen3-1.7b-v1/`](../../results/campaigns/smoke-qwen3-1.7b-v1/).

| Dimension | Run details |
|---|---|
| Hardware | GTX 1050 Ti, 4 GiB; Ryzen 5 3600; GPU Lab/CT108 |
| Model | Qwen3-1.7B Q4_K_M, GGUF; Apache-2.0 |
| GGUF SHA-256 | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` |
| Quality harness | EleutherAI lm-evaluation-harness `0.4.14.dev0`, commit `d6de81643928d653435c431bae19945d41d32520` |
| Runtime | llama.cpp build 12024, commit `ddf48f85c` |
| Sample | limit 20 per task; seed 42 |

### Quality

Values are taken from the harness JSON; `acc_norm` is reported where available.

| Task | Metric | Value | n |
|---|---|---:|---:|
| ARC Challenge | acc / acc_norm | 0.350 / 0.400 | 20 |
| HellaSwag | acc / acc_norm | 0.400 / 0.400 | 20 |
| Belebele (Portuguese, `por_Latn`) | acc / acc_norm | 0.750 / 0.750 | 20 |
| GSM8K | exact match (strict / flexible) | 0.000 / 0.000 | 20 |
| IFEval | prompt strict / loose | 0.600 / 0.550 | 20 |
| IFEval | instance strict / loose | 0.667 / 0.633 | 20 |

Harness-reported metrics and standard errors, task versions, hashes, configurations, and samples are preserved in `knowledge-mcq/results.json` and `generative-chat/results.json`, with their `meta.json` manifests and logs.

### Performance

Measured with `llama-bench`, CUDA, 99 GPU layers, F16 KV cache, three repetitions:

| Operation | Size | Mean | Standard deviation |
|---|---:|---:|---:|
| Prefill | 512 tokens | 850.305 tokens/s | 1.123 |
| Decode | 128 tokens | 48.155 tokens/s | 0.023 |

Per-repetition values and original output are in `llama-bench/results.json` and `llama-bench/run.log`.

## Protocol and limitations

- This is a **smoke campaign**, not a comparative benchmark: `limit=20` checks integration and provenance. This small sample does not support rankings or generalizable conclusions.
- The campaign used zero-shot (`num_fewshot=0`), including GSM8K, whose harness task default is 5-shot. These values are not directly comparable to runs using the task defaults.
- The harness warned that it could not infer the EOS stop sequence. The run completed, but this may affect generation fidelity and must be resolved before comparative evaluation.
- A one-item isolated reproduction with the original thinking behavior returned empty `message.content`, non-empty `reasoning_content`, and `finish_reason=length` at both 256 and 384 output tokens; the harness response exactly matched the empty `message.content`. With Qwen3 chat-template kwargs `enable_thinking=false`, the same prompt returned content and stopped normally, but did not use GSM8K's expected `#### <number>` format. The pinned strict filter therefore returned `[invalid]`; the flexible filter selected the final LaTeX `$$` delimiter after the boxed answer. This is a prompt/output-format mismatch, not a defect in the official harness. It was observed on one sample only.
- The original smoke artifacts and score remain unchanged. The orchestrator now forwards configured `max_gen_toks` (default 256), optional `eos_string`, and optional server `chat_template_kwargs` for future runs. The one-item test does not establish what would happen across the remaining 19 examples or justify a score correction; the official task/filter was not modified.
- The command recorded `--apply_chat_template` and the server was started with `--jinja`; however, the harness JSON records an empty `chat_template` and null hash. The effective template provenance is therefore not proven by the current artifacts.
- The `llama-bench` manifest's version field contains usage text, not a semantic version. The verifiable identity is build 12024 and commit `ddf48f85c` in the benchmark output.
- The campaign ran on one physical GPU. Historical repository results are a separate experimental series and must not be merged with this campaign.

## Reproduction

From the repository root, with `llama-server`, `llama-bench`, and the harness at the recorded version/commit, run inside the isolated GPU Lab environment:

```bash
python -m llm_research_bench.campaign plan --spec configs/campaigns/smoke-qwen3-1.7b.yaml
python -m llm_research_bench.campaign run --spec configs/campaigns/smoke-qwen3-1.7b.yaml
python -m llm_research_bench.campaign summary --out results/campaigns
```

The manifests and raw outputs under `results/campaigns/` are the provenance source of truth; the summary values above do not replace those artifacts.

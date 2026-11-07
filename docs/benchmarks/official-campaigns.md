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
- A separate 20-item GSM8K diagnostic used `enable_thinking=false`, zero-shot, seed 42, `max_gen_toks=384`, `eos_string=<|im_end|>`, and the pinned harness. All 20 API contents matched the harness responses; no `####` marker was present. Generation stopped normally for 18/20 and hit the token limit for 2/20; `reasoning_content` was absent. The effective server template was observed via `/props` (SHA-256 `87a2728cb8dc9fe424d624542f6060ec05a1d285ebbec578bb078900e33396b5`).
- On that diagnostic, the official strict filter returned `[invalid]` for 20/20. The flexible filter marked 0/20 invalid but extracted `$$` for 9/20, so its invalid rate does not mean the extraction is correct. The model’s output format is incompatible with GSM8K’s expected `#### <number>` format; official tasks/filters were not changed and no accuracy claim is made. See `results/diagnostics/pr9-gsm8k-n20-20261101T174900Z/` for sanitized requests/responses, per-item analysis, effective server props, model identity, and harness outputs.
- The sandbox entrypoint now has a fixed `GPU_LAB_TASK=gsm8k-paired` mode that runs only `tools/homelab/gsm8k-diagnostic.sh`; the default remains the full campaign, and other task values are rejected before setup. Select this mode in the environment of an already-authorized `gpu-lab job`; it accepts no command or script argument. **The paired run remains pending** because this repository does not document how the external restricted gateway forwards that environment variable. No gateway bypass, access/configuration change, or remote job was attempted; comparison findings and any larger validation remain pending until the gateway’s supported environment-setting interface is confirmed.
- The earlier one-item thinking-on diagnostic returned empty `message.content`, non-empty `reasoning_content`, and `finish_reason=length` at caps 256 and 384; the harness faithfully returned the empty content. This behavior was not observed in the 20-item no-thinking run. The original smoke artifacts and score remain unchanged; diagnostics are a separate series and do not justify a score correction.
- The original smoke artifacts have no verified effective chat-template provenance: their harness JSON has an empty template/hash. The separate diagnostic records the observed server template through `/props`. The orchestrator forwards configured `max_gen_toks` (default 256), optional `eos_string`, and optional server `chat_template_kwargs` for future runs.
- The `llama-bench` manifest's version field contains usage text, not a semantic version. The verifiable identity is build 12024 and commit `ddf48f85c` in the benchmark output.
- The campaign ran on one physical GPU. Historical repository results are a separate experimental series and must not be merged with this campaign.

## GPU Lab campaign v2: Qwen3-1.7B on the GTX 1050 Ti (exploratory)

Complete artifacts: [`results/campaigns/gpu-lab-qwen3-1.7b-v2/`](../../results/campaigns/gpu-lab-qwen3-1.7b-v2/).
Spec: [`configs/campaigns/gpu-lab-qwen3-1.7b-v2.yaml`](../../configs/campaigns/gpu-lab-qwen3-1.7b-v2.yaml).

**Status: exploratory.** The protocol was not preregistered and one hardware
configuration was measured once, so these values describe this run. They do not
support model rankings, and they are not comparable to the smoke campaign's
limit-20 scores.

| Dimension | Run details |
|---|---|
| Hardware | GTX 1050 Ti, 4 GiB; Ryzen 5 3600; GPU Lab CT108 (LXC 108 on Proxmox `v01`) |
| Model | Qwen3-1.7B Q4_K_M (1,276,487,680 bytes as loaded; 2,031,739,904 params) |
| GGUF SHA-256 | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` |
| Quality harness | lm-evaluation-harness `0.4.14.dev0`, pinned commit `d6de81643928d653435c431bae19945d41d32520` |
| Runtime | llama.cpp `0.8.0-dev`, build 12024, commit `ddf48f85c`, CUDA build |
| Server | ctx 4096, 99 GPU layers, 2 threads, `--parallel 1`, `enable_thinking=false`, `--cache-ram 0` |
| Sample | limit 100 per task (first N, deterministic); seed 42; zero-shot |
| Execution | one gpu-lab `job` lease, generation 168 |

### Quality (n=100 per task)

95% Wilson score intervals treat the 100 items as Bernoulli draws. They describe
item-sampling uncertainty, not run-to-run variance.

| Task | Metric | Value | 95% CI |
|---|---|---:|---|
| ARC Challenge | acc | 0.470 | 0.375–0.567 |
| ARC Challenge | acc_norm | 0.470 | 0.375–0.567 |
| HellaSwag | acc | 0.440 | 0.347–0.538 |
| HellaSwag | acc_norm | 0.470 | 0.375–0.567 |
| GSM8K | exact match, strict | 0.000 | 0.000–0.037 |
| GSM8K | exact match, flexible extraction | 0.460 | 0.366–0.557 |
| IFEval | prompt-level strict | 0.680 | 0.583–0.763 |
| IFEval | prompt-level loose | 0.720 | 0.625–0.799 |
| IFEval | instruction-level strict | 0.755 | 0.662–0.829 |
| IFEval | instruction-level loose | 0.791 | 0.702–0.860 |

The GSM8K gap is a **formatting effect**, not evidence that the model cannot do
arithmetic: strict match requires the `#### <number>` marker, and these
generations end with the answer in prose. Strict and flexible extraction use the
same final-answer comparison. Spot-checked raw responses show correct reasoning
chains that end without the marker.

### Throughput (llama-bench, 10 repetitions)

| Operation | Tokens | Mean | SD | SEM | 95% CI (t, df=9) |
|---|---|---:|---:|---:|---|
| Prefill | 512 | 848.835 tok/s | 1.892 | 0.598 | 847.48–850.19 |
| Decode | 128 | 48.030 tok/s | 0.015 | 0.005 | 48.020–48.041 |

`llama-bench` runs its own process with 6 threads and does not use the evaluation
server, so it is unaffected by `--cache-ram`. Warm-up is negligible: the first
repetition is 0.33% faster than the mean of the remaining nine for prefill and
0.04% faster for decode, both inside the reported interval.

### Observed wall-clock and memory

- Knowledge group: 200 items in 216 s (1.08 s/item).
- Generative group: 200 items in 1,064 s (5.32 s/item); IFEval's long
  generations dominate.
- GPU memory in use during evaluation: 1.21–1.61 GiB (spot checks with
  `nvidia-smi`, 2 samples). This is not a trace; no peak allocator metric was
  collected.
- GPU utilization 88–98% during evaluation (spot checks).
- No power, clock, or temperature series was collected, so no tokens-per-joule
  or thermal-throttling claim is made.

### What this run does and does not establish

- **Reproducible:** a second lease re-ran the knowledge group and returned
  identical scores (ARC 0.47/0.47, HellaSwag 0.44/0.47), which is expected at
  temperature 0 on a fixed item subset. This is a consistency check, not a
  variance estimate across hardware states.
- **Not independent replicates:** 100 items per task are not 100 hardware
  replicates, and the two groups share one GPU, one lease, and one thermal
  history.
- **Confounders:** the sandbox caps the job at 3 GiB of host memory and 1.5
  CPUs; the server used 2 threads while `llama-bench` used 6; the LXC host runs
  other services. Latency per item therefore includes queueing and preemption
  effects that a dedicated workstation would not show.
- **One aborted attempt:** the first generative run (generation 167) was killed
  by the container's memory cgroup at 50/200 requests because the llama.cpp host
  prompt cache is unbounded by default. The completed run pins `--cache-ram 0`.
  The aborted attempt produced no quality values and is retained in the log
  history only.

### gpu-lab lifecycle: preemption, bug, and restoration

The GPU is not "stuck": the production inference service (Qwen3.5-4B) is the
idle owner of the card. The lab lease preempts it for the duration of a job and
restores it afterwards; external inference is refused with HTTP 503 while the
lease is held.

A scheduler bug surfaced during the first attempt: the reaper
(`gpu-lab-controller reap`, run by the 30 s watchdog) treated a job attempt as
orphaned during the acquire window, because the supervisor record is only
written at bind time. It restored production mid-acquire and then rejected the
grant. The fix makes the job branch reap only when a supervisor record exists and
its PID is dead; the lease TTL covers the pre-bind window. Backup:
`/root/gpu_lab_controller.py.bak-20261105T124243Z`. `gpu-labctl reconcile`
reports `healthy`.

Restoration evidence for the completed run: terminal attempt for generation 168
is `mode=job`, `reason=supervisor_stopped`, `result=restored`; controller state
returned to `production/production`; the production gateway answered
`GET /health` with HTTP 200 afterwards.

### Limitations

- Not preregistered; no confirmatory hypothesis was fixed in advance.
- One model, one quantization, one GPU, one lease per configuration.
- `--limit 100` is the first 100 items, not a random or stratified sample.
- Zero-shot throughout; GSM8K's harness default is 5-shot, so these values are
  not comparable to default-protocol GSM8K numbers.
- No power, clock, or temperature telemetry; no thermal steady-state control.
- Accuracy intervals assume independent items; benchmark items often cluster.

### Proposed follow-up protocol

The lease-controller stress tests, the artifact audit and the expanded follow-up
protocol are in [`gpu-lab-hardening.md`](gpu-lab-hardening.md).

1. Preregister the hypothesis, primary metrics, and the analysis, including the
   multiple-comparison family.
2. Five independent leases per configuration, randomized order, with a fixed
   cool-down and a recorded GPU temperature before each lease.
3. Sample clocks, power, temperature, and memory at 1 Hz for the whole run
   (`nvidia-smi --query-gpu=... --loop-ms=1000`), and report tokens per joule
   only when the power sensor is actually present.
4. Run full task splits (no `--limit`), 5-shot GSM8K, and an EOS/stop-sequence
   ablation to separate formatting failures from capability failures.
5. Analyse items with a paired bootstrap across the shared item set, and report
   the minimum detectable effect for the planned sample size.

## Reproduction

From the repository root, with `llama-server`, `llama-bench`, and the harness at the recorded version/commit, run inside the isolated GPU Lab environment:

```bash
python -m llm_research_bench.campaign plan --spec configs/campaigns/smoke-qwen3-1.7b.yaml
python -m llm_research_bench.campaign run --spec configs/campaigns/smoke-qwen3-1.7b.yaml
python -m llm_research_bench.campaign summary --out results/campaigns
```

The manifests and raw outputs under `results/campaigns/` are the provenance source of truth; the summary values above do not replace those artifacts.

For campaign v2 the same commands run inside a gpu-lab lease, which preempts
production inference and restores it on exit:

```bash
ssh gpu-lab-ander@192.168.1.23 'job repo/tools/homelab/run-gpu-lab-v2.sh'
```

The wrapper pins `SPEC=repo/configs/campaigns/gpu-lab-qwen3-1.7b-v2.yaml`,
`MODELS_DIR=/models` and calls `tools/homelab/campaign-entrypoint.sh`; the
supervisor acquires the lease, binds it, and releases it as `finished` or
`supervisor_stopped`. Figure:

```bash
python -m llm_research_bench.campaign_figures \
  --summary results/campaigns/summary.json \
  --campaign gpu-lab-qwen3-1.7b-v2 \
  --output reports/figures/gpu-lab-qwen3-1.7b-v2
```
